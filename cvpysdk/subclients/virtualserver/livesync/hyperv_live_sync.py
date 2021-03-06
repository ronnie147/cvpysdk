# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# Copyright Commvault Systems, Inc.
# See LICENSE.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""File for configuring and monitoring live sync on the Hyper-V subclient.

HyperVLiveSync is the only class defined in this file.

HyperVLiveSync: Class for configuring and monitoring Hyper-V subclient live sync

HyperVLiveSync:

    generate_restore_options_json()     -- To generate the restore options json for Hyper-V live sync

"""

from past.builtins import basestring

from .vsa_live_sync import VsaLiveSync
from ....exception import SDKException


class HyperVLiveSync(VsaLiveSync):
    """Class for configuring and monitoring Hyper-V live sync operations"""

    def configure_live_sync(self,
                            schedule_name=None,
                            destination_client=None,
                            proxy_client=None,
                            vm_to_restore=None,
                            destination_path=None,
                            power_on=True,
                            overwrite=False,
                            distribute_vm_workload=None,
                            restored_vm_name=None,
                            restore_option=None,
                            pattern_dict=None
                            ):
        """To configure live

        Args:

            schedule_name               (str)   -- Name of the Live sync schedule to be created

            destination_client          (str)   -- Hyperv Host Client Name where VM needs to be restored

            proxy_client                (str)   -- Name of the proxy client to be used

            vm_to_restore               (list)  -- VM's to be restored

            destination_path            (str)   -- Full path of the restore location on client

            power_on                    (bool)  -- To validate destination VM power on and off
                                                    default: True

            overwrite                   (bool)  -- To overwrite VM and VHDs in destination path
                                                    default: False

            distribute_vm_workload      (int)   -- Virtual machines to be used per job

            restored_vm_name            (str)   -- Name used for the VM when restored

            restore_option              (dict)  -- Restore options dictionary with advanced options

            pattern_dict                (dict)  -- Dictionary to generate the live sync schedule

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

        """
        # restore options
        if restore_option is None:
            restore_option = {}

        if vm_to_restore and not isinstance(vm_to_restore, basestring):
            raise SDKException('Subclient', '101')

        if not restored_vm_name and isinstance(vm_to_restore, basestring):
            restored_vm_name = "Delete" + vm_to_restore
        restore_option['restore_new_name'] = restored_vm_name

        if vm_to_restore:
            vm_to_restore = [vm_to_restore]

        # check mandatory input parameters are correct
        if bool(restore_option):
            if not (isinstance(destination_path, basestring) and
                    isinstance(overwrite, bool) and
                    isinstance(power_on, bool)):
                raise SDKException('Subclient', '101')

        # set attr for all the option in restore xml from user inputs
        self._subclient_object._set_restore_inputs(
            restore_option,
            vm_to_restore=self._subclient_object._set_vm_to_restore(vm_to_restore),
            unconditional_overwrite=overwrite,
            power_on=power_on,
            distribute_vm_workload=distribute_vm_workload,
            copy_precedence=0,
            volume_level_restore=1,
            vcenter_client=destination_client,
            client_name=proxy_client,
            esx_server=proxy_client,
            esx_host=proxy_client,
            datastore=destination_path,
            in_place=False
        )

        return self._configure_live_sync(schedule_name, restore_option, pattern_dict)
