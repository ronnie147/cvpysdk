# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# Copyright Commvault Systems, Inc.
# See LICENSE.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""" Main file for performing the download operation

Download
========

    __init__(commcell_object)        --  initialize commcell_object of Install class
    associated with the commcell

    push_servicepack_and_hotfix()    --  installs the latest service pack in the client machine

    install_software                 --  Installs the features selected on the machines selected

"""

from ..job import Job
from ..exception import SDKException


class Install(object):
    """"class for installing software packages"""

    def __init__(self, commcell_object):
        """Initialize object of the Install class.

            Args:
                commcell_object (object)  --  instance of the Commcell class

            Returns:
                object - instance of the Install class

        """

        self.commcell_object = commcell_object
        self._services = commcell_object._services
        self._cvpysdk_object = commcell_object._cvpysdk_object

    def push_servicepack_and_hotfix(
            self,
            client_computers=None,
            client_computer_groups=None,
            all_client_computers=False,
            all_client_computer_groups=False,
            reboot_client=False,
            run_db_maintenance=True):
        """Installs the software packages on the clients

        Args:
            client_computers (list)               -- Client machines to install service pack on

            client_computer_groups (list)         -- Client groups to install service pack on

            all_client_computers (bool)           -- boolean to specify whether to install on
            all client computers or not

                default: False

            all_client _computer_groups (bool)    -- boolean to specify whether to install on all
            client computer groups or not

                default: False

            reboot_client (bool)                  -- boolean to specify whether to reboot the
            client or not

                default: False

            run_db_maintenance (bool)             -- boolean to specify whether to run db
            maintenance not

                default: True

        Returns:
            object - instance of the Job class for this download job

        Raises:
                SDKException:
                    if Download job failed

                    if response is empty

                    if response is not success

                    if another download job is already running

        **NOTE:** push_serivcepack_and_hotfixes cannot be used for revision upgrades

        """
        selected_clients = []
        selected_client_groups = []

        if not any([all_client_computers,
                    all_client_computer_groups,
                    client_computers,
                    client_computer_groups]):
            raise SDKException('Install', '101')

        commcell_client_computers = self.commcell_object.clients.all_clients
        commcell_client_computer_groups = self.commcell_object.client_groups.all_clientgroups

        if client_computers is not None:
            client_computers = [x.lower() for x in client_computers]
            if not set(client_computers).issubset(commcell_client_computers):
                raise SDKException('Install', '102')

            selected_clients = [{'clientName': client} for client in client_computers]

        if client_computer_groups is not None:
            client_computer_groups = [x.lower() for x in client_computer_groups]
            if not set(client_computer_groups).issubset(commcell_client_computer_groups):
                raise SDKException('Install', '103')

            selected_client_groups = [{'clientGroupName': client}
                                      for client in client_computer_groups]

        if all_client_computers:
            selected_clients = [{"_type_": 2}]

        if all_client_computer_groups:
            selected_client_groups = [{"_type_": 27}]

        all_clients = selected_clients + selected_client_groups

        request_json = {
            "taskInfo": {
                "task": {
                    "taskType": 1,
                    "initiatedFrom": 2,
                    "policyType": 0,
                    "alert": {
                        "alertName": ""
                    },
                    "taskFlags": {
                        "isEdgeDrive": False,
                        "disabled": False
                    }
                },
                "subTasks": [
                    {
                        "subTaskOperation": 1,
                        "subTask": {
                            "subTaskType": 1,
                            "operationType": 4020
                        },
                        "options": {
                            "adminOpts": {
                                "updateOption": {
                                    "removeIntersectingDiag": True,
                                    "restartExplorerPlugin": True,
                                    "rebootClient": reboot_client,
                                    "runDBMaintenance": run_db_maintenance,
                                    "clientAndClientGroups": all_clients,
                                    "installUpdatesJobType": {
                                        "upgradeClients": False,
                                        "undoUpdates": False,
                                        "installUpdates": True
                                    }
                                }
                            },
                        }
                    }
                ]
            }
        }
        flag, response = self._cvpysdk_object.make_request(
            'POST', self._services['CREATE_TASK'], request_json
        )

        if flag:
            if response.json():
                if "jobIds" in response.json():
                    return Job(self.commcell_object, response.json()['jobIds'][0])

                else:
                    raise SDKException('Install', '107')

            else:
                raise SDKException('Response', '102')
        else:
            raise SDKException('Response', '101')

    def install_software(
            self,
            client_computers=None,
            windows_features=None,
            unix_features=None,
            username=None,
            password=None):
        """
        Installs the features selected on the given machines
        Args:

            client_computers    (list)      -- list of hostnames/IP address to install the
            features on

                default : None

            windows_features (list of enum) -- list of windows features to be installed

                default : None

            unix_features (list of enum)    -- list of unix features to be installed

                default : None

            username    (str)               -- username of the machine to install features on

                default : None

            password    (str)               -- base64 encoded password

                default : None

        Returns:
                object - instance of the Job class for this install_software job

        Raises:
            SDKException:
                if install job failed

                if response is empty

                if response is not success

        Usage:

            -   UnixDownloadFeatures and WindowsDownloadFeatures enum is used for providing
                input to the install_software method, it can be imported by

                >>> from cvpysdk.deployment.deploymentconstants import UnixDownloadFeatures
                    from cvpysdk.deployment.deploymentconstants import WindowsDownloadFeatures

            -   sample method call

                >>> commcell_obj.install_software(
                                client_computers=[win_machine1, win_machine2],
                                windows_features=[WindowsDownloadFeatures.FILE_SYSTEM.value],
                                unix_features=None,
                                username='username',
                                password='password')

                    **NOTE:** Either Unix or Windows clients_computers should be chosen and
                    not both

        """
        if windows_features:
            os_type = 0
            install_options = [{'osType': 'Windows', 'ComponentId': feature_id}
                               for feature_id in windows_features]

        elif unix_features:
            os_type = 1
            install_options = [{'osType': 'Unix', 'ComponentId': feature_id}
                               for feature_id in windows_features]

        else:
            raise SDKException('Install', '105')

        if client_computers:
            commcell_name = self.commcell_object.commserv_name

            client_details = []
            for client_name in client_computers:
                client_details.append(
                    {
                        "clientEntity": {
                            "clientName": client_name,
                            "commCellName": commcell_name
                        }
                    })

        else:
            raise SDKException('Install', '106')

        request_json = {
            "taskInfo": {
                "associations": [
                    {
                        "commCellId": 2
                    }
                ],
                "task": {
                    "taskType": 1,
                    "initiatedFrom": 1,
                    "taskFlags": {
                        "disabled": False
                    }
                },
                "subTasks": [
                    {
                        "subTask": {
                            "subTaskType": 1,
                            "operationType": 4026
                        },
                        "options": {
                            "adminOpts": {
                                "clientInstallOption": {
                                    "reuseADCredentials": False,
                                    "installOSType": os_type,
                                    "discoveryType": 0,
                                    "installerOption": {
                                        "requestType": 0,
                                        "Operationtype": 0,
                                        "CommServeHostName":
                                            self.commcell_object.commserv_hostname,
                                        "RemoteClient": False,
                                        "installFlags": {
                                            "allowMultipleInstances": True,
                                            "restoreOnlyAgents": False,
                                            "killBrowserProcesses": True,
                                            "install32Base": False,
                                            "disableOSFirewall": False,
                                            "stopOracleServices": False,
                                            "skipClientsOfCS": False,
                                            "addToFirewallExclusion": True,
                                            "ignoreJobsRunning": False,
                                            "forceReboot": False,
                                            "overrideClientInfo": True,
                                            "firewallInstall": {
                                                "enableFirewallConfig": False,
                                                "firewallConnectionType": 0,
                                                "portNumber": 0
                                            }
                                        },
                                        "User": {
                                            "userName": "admin",
                                            "userId": 1
                                        },
                                        "clientComposition": [
                                            {
                                                "packageDeliveryOption": 0,
                                                "overrideSoftwareCache": False,
                                                "components": {
                                                    "commonInfo": {
                                                        "globalFilters": 2
                                                    },
                                                    "fileSystem": {
                                                        "configureForLaptopBackups": False
                                                    },
                                                    "componentInfo": install_options,
                                                },
                                                "clientInfo": {
                                                    "client": {
                                                        "evmgrcPort": 0,
                                                        "cvdPort": 0
                                                    }
                                                }
                                            }
                                        ]
                                    },
                                    "clientDetails": client_details,
                                    "clientAuthForJob": {
                                        "password": password,
                                        "userName": username
                                    }
                                },
                                "updateOption": {
                                    "rebootClient": True
                                }
                            }
                        }
                    }
                ]
            }
        }
        flag, response = self._cvpysdk_object.make_request(
            'POST', self._services['CREATE_TASK'], request_json
        )

        if flag:
            if response.json():
                if "jobIds" in response.json():
                    return Job(self.commcell_object, response.json()['jobIds'][0])

                else:
                    raise SDKException('Install', '107')

            else:
                raise SDKException('Response', '102')
        else:
            raise SDKException('Response', '101')
