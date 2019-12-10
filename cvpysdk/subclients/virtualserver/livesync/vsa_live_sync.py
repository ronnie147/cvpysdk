# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# Copyright Commvault Systems, Inc.
# See LICENSE.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""File for configuring and monitoring live sync on the VSA subclient.

VsaLiveSync and LiveSyncPair are the 2 classes defined in this file.

VsaLiveSync: Class for configuring virtual server agent live sync

LiveSyncPair: Class for monitoring and configuring a Live sync pair


VsaLiveSync:
============

    __init__(subclient_object)      -- Initializing instance of the VsaLiveSync class

     __str__()                      -- Returns all the Live sync pairs associated with the subclient

    __repr__()                      -- Returns the string to represent the instance of the VsaLiveSync class

    _get_live_sync_pairs()          -- Gets all the live sync pairs associated with the subclient

    _live_sync_subtask_json()       -- Returns subtask JSON for live sync

    _configure_live_sync()          -- To configure live sync

    get()                           -- Returns a LiveSyncPair object for the given live sync name

    has_live_sync_pair()            -- Checks if a live sync pair exists with the given name

    refresh()                       -- Refresh the live sync pairs associated with the subclient


VsaLiveSync Attributes:
-----------------------

    **live_sync_pairs**     -- Returns the dictionary of all the live sync pairs and their info


LiveSyncPair:
=============

    __init__(subclient_object)      -- Initializing instance of the LiveSyncPair class

    __repr__()                      -- Returns the string to represent the instance of the LiveSyncPair class

    _get_live_sync_id()             -- Gets the live sync pair id associated with this subclient

    _get_live_sync_properties()     -- Gets the live sync properties of this live sync

    refresh()                       -- Refreshes the properties of the live sync


LiveSyncPairs Attributes:
-------------------------

    **live_sync_id**        -- Returns the ID of the live sync pair

    **live_sync_name**      -- Returns the name of the live sync pair

    **replication_guid**    -- Returns the replication guid of the live sync pair

    **source_vm**           -- Returns the name of the source virtual machine

    **destination_vm**      -- Returns the name of the destination virtual machine

    **status**              -- Returns the status of the live sync pair

"""

import uuid

from past.builtins import basestring

from ....constants import HypervisorType as hv_type
from ....constants import VSALiveSyncStatus as sync_status
from ....exception import SDKException
from ....schedules import SchedulePattern


class VsaLiveSync:
    """Class for configuring and monitoring virtual server live sync operations"""

    def __new__(cls, subclient_object):
        """Decides which instance object needs to be created"""
        instance_name = subclient_object._instance_object.instance_name

        if instance_name == hv_type.MS_VIRTUAL_SERVER.value.lower():
            from .hyperv_live_sync import HyperVLiveSync
            return object.__new__(HyperVLiveSync)
        raise SDKException(
            'LiveSync',
            '102',
            'Virtual server Live Sync for Instance: "{0}" is not yet supported'.format(instance_name)
        )

    def __init__(self, subclient_object):
        """Initializing instance of the VsaLiveSync class

        Args:
            subclient_object    (obj)   -- Instance of Subclient class

        """
        self._subclient_object = subclient_object
        self._subclient_id = self._subclient_object.subclient_id
        self._subclient_name = self._subclient_object.name

        self.schedule_pattern = SchedulePattern()

        self._live_sync_pairs = None

        self._commcell_object = self._subclient_object._commcell_object
        self._cvpysdk_object = self._commcell_object._cvpysdk_object
        self._services = self._commcell_object._services
        self._update_response_ = self._commcell_object._update_response_

        self._ALL_LIVE_SYNC_PAIRS = self._services['GET_ALL_LIVE_SYNC_PAIRS'] % self._subclient_id

        self.refresh()

    def __str__(self):
        """Representation string consisting of all Live sync pairs of the subclient.

        Returns:
            str - string of all the live sync pairs associated with the subclient

        """
        representation_string = '{:^5}\t{:^20}\n\n'.format('S. No.', 'LiveSyncPair')

        for index, live_sync in enumerate(self.live_sync_pairs):
            sub_str = '{:^5}\t{:20}\n'.format(index + 1, live_sync)
            representation_string += sub_str

        return representation_string.strip()

    def __repr__(self):
        """String representation of the instance of this class.

        Returns:
            str - string about the details of the VSALiveSync class instance

        """
        return 'VSALiveSync class instance for the Subclient: "{0}"'.format(self._subclient_name)

    def _get_live_sync_pairs(self):
        """Gets all the live sync pairs associated with the subclient

        Returns:
            dict    -- consists of all the live sync pairs in the subclient

                {
                    "live_sync_pair1_name": {
                                "id": live_sync_pair1_id
                    },
                    "live_sync_pair2_name": {
                                "id": live_sync_pair2_id
                    },
                }

        Raises:
                SDKException:
                    if response is empty

                    if response is not success

        """
        flag, response = self._cvpysdk_object.make_request('GET', self._ALL_LIVE_SYNC_PAIRS)

        if flag:
            live_sync_pairs_dict = {}
            if not bool(response.json()):
                return live_sync_pairs_dict
            elif response.json() and 'siteInfo' in response.json():
                for dictionary in response.json()['siteInfo']:
                    temp_name = dictionary['subTask']['subtaskName'].lower()
                    temp_id = str(dictionary['replicationId'])
                    live_sync_pairs_dict[temp_name] = {
                        'id': temp_id
                    }

                return live_sync_pairs_dict

            raise SDKException('Response', '102')

        raise SDKException('Response', '101', self._update_response_(response.text))

    @staticmethod
    def _live_sync_subtask_json(schedule_name):
        """setter for the subtask in live sync JSON

        Args:
            schedule_name   (str)   -- Name of the Live sync schedule to be created

        """
        return {
            "subTaskType": "RESTORE",
            "operationType": "SITE_REPLICATION",
            "subTaskName": schedule_name
        }

    def _configure_live_sync(self, schedule_name, restore_options, pattern_dict=None):
        """Configures Live sync after generating the full live sync json

        Args:
            schedule_name       (str)   -- Name of the Live sync schedule to be created

            restore_options     (dict)  -- Dictionary with all necessary values for Live sync

            pattern_dict        (dict)  -- Dictionary to generate the live sync schedule

                Sample:

                    for after_job_completes :
                    {
                        "freq_type": 'after_job_completes',
                        "active_start_date": date_in_%m/%d/%y (str),
                        "active_start_time": time_in_%H/%S (str),
                        "repeat_days": days_to_repeat (int)
                    }

                    for daily:
                    {
                         "freq_type": 'daily',
                         "active_start_time": time_in_%H/%S (str),
                         "repeat_days": days_to_repeat (int)
                    }

                    for weekly:
                    {
                         "freq_type": 'weekly',
                         "active_start_time": time_in_%H/%S (str),
                         "repeat_weeks": weeks_to_repeat (int)
                         "weekdays": list of weekdays ['Monday','Tuesday']
                    }

                    for monthly:
                    {
                         "freq_type": 'monthly',
                         "active_start_time": time_in_%H/%S (str),
                         "repeat_months": weeks_to_repeat (int)
                         "on_day": Day to run schedule (int)
                    }

                    for yearly:
                    {
                         "active_start_time": time_in_%H/%S (str),
                         "on_month": month to run schedule (str) January, Febuary...
                         "on_day": Day to run schedule (int)
                    }

        Returns:
            object - instance of the Schedule class for this Live sync

        **Note** use this method to generate full Live sync JSON and to post the API call in derived class

        """
        # To generate a random UUID for replication
        restore_options['replication_guid'] = str(uuid.uuid1())

        request_json = self._subclient_object._prepare_fullvm_restore_json(restore_options)

        # To include the schedule pattern
        request_json = self.schedule_pattern.create_schedule(
            request_json,
            pattern_dict or {'freq_type': 'after_job_completes'})

        request_json['taskInfo']['subTasks'][0]['subTask'] = self._live_sync_subtask_json(schedule_name)

        return self._subclient_object._process_restore_response(request_json)

    @property
    def live_sync_pairs(self):
        """Returns the dictionary of all the live sync pairs and their info

        Returns:
            dict    -- consists of all the live sync pairs in the subclient

                {
                    "live_sync_pair1_name": {
                                "id": live_sync_pair1_id
                    },
                    "live_sync_pair2_name": {
                                "id": live_sync_pair2_id
                    },
                }

        """
        return self._live_sync_pairs

    def get(self, live_sync_name):
        """Returns a LiveSyncPair object for the given live sync name

        Args:
             live_sync_name     (str)   -- Name of the live sync

        Returns:
            object  - Instance of the LiveSyncPair class for the given live sync name

        Raises:
            SDKException:
                if type of the live sync name argument is not string

        """
        if not isinstance(live_sync_name, basestring):
            raise SDKException('LiveSync', '101')
        if self.has_live_sync_pair(live_sync_name):
            return LiveSyncPair(
                self._subclient_object,
                live_sync_name,
                self.live_sync_pairs[live_sync_name]['id'])
        raise SDKException(
            'LiveSync', '102', 'No Live Sync exists with given name: {0}'.format(live_sync_name)
        )

    def has_live_sync_pair(self, live_sync_name):
        """Checks if a live sync pair exists with the given name

        Args:
            live_sync_name      (str)   -- Name of the live sync

        Returns:
                bool    -   boolean output whether the client exists in the commcell or not

        Raises:
            SDKException:
                if type of the live sync name argument is not string

        """
        return self.live_sync_pairs and live_sync_name.lower() in self.live_sync_pairs

    def refresh(self):
        """Refresh the live sync pairs associated with the subclient"""
        self._live_sync_pairs = self._get_live_sync_pairs()


class LiveSyncPair:
    """Class for monitoring a live sync"""

    def __init__(self, subclient_object, live_sync_name, live_sync_id=None):
        """Initializing instance of the LiveSyncPair class

         Args:
            subclient_object    (obj)   -- Instance of Subclient class

            live_sync_name      (str)   -- Name of the Live sync

            live_sync_id        (str)   -- ID of the live sync

        """
        self._subclient_object = subclient_object
        self._subclient_id = self._subclient_object.subclient_id
        self._subclient_name = self._subclient_object.name

        self._live_sync_name = live_sync_name.lower()

        self._commcell_object = self._subclient_object._commcell_object
        self._cvpysdk_object = self._commcell_object._cvpysdk_object
        self._services = self._commcell_object._services
        self._update_response_ = self._commcell_object._update_response_

        self._live_sync_id = live_sync_id or self._get_live_sync_id()

        self._LIVE_SYNC_PAIR = self._services['GET_LIVE_SYNC_PAIR'] % (
            self._subclient_id,
            self.live_sync_id
        )

        self._properties = None
        self._replication_guid = None
        self._status = None
        self._source_vm = None
        self._destination_vm = None

        self.refresh()

    def __repr__(self):
        """String representation of the instance of this class."""
        representation_string = 'LiveSyncPair class instance for Subclient: "{0}"'
        return representation_string.format(self._subclient_name)

    def _get_live_sync_id(self):
        """Gets the live sync pair id associated with this subclient

        Returns:
            str - id associated with this Live sync pair

        """
        return self._subclient_object.live_sync.get(self.live_sync_name).live_sync_id

    def _get_live_sync_properties(self):
        """Gets the live sync properties of this live sync

        Raises:
            SDKException:
                if response is empty

                if response is not success

        """
        flag, response = self._cvpysdk_object.make_request('GET', self._LIVE_SYNC_PAIR)

        if flag:
            if not bool(response.json()):
                pass
            elif response.json() and 'siteInfo' in response.json():
                self._properties = response.json()['siteInfo'][0]
                self._replication_guid = self._properties['replicationGuid']
                self._status = self._properties['status']
                self._source_vm = self._properties['sourceName']
                self._destination_vm = self._properties['destinationName']
            else:
                raise SDKException('Response', '102')
        else:
            raise SDKException('Response', '101', self._update_response_(response.text))

    @property
    def live_sync_id(self):
        """Treats the live sync id as a read-only attribute."""
        return self._live_sync_id

    @property
    def live_sync_name(self):
        """Treats the live sync name as a read-only attribute."""
        return self._live_sync_name

    @property
    def replication_guid(self):
        """Treats the replication guid as a read-only attribute."""
        return self._replication_guid

    @property
    def source_vm(self):
        """Treats the source VM as a read-only attribute."""
        return self._source_vm

    @property
    def destination_vm(self):
        """Treats the destination VM as a read-only attribute."""
        return self._destination_vm

    @property
    def status(self):
        """Treats the status as a read-only attribute."""
        return sync_status(self._status).name

    def refresh(self):
        """Refreshes the properties of the live sync"""
        self._get_live_sync_properties()
