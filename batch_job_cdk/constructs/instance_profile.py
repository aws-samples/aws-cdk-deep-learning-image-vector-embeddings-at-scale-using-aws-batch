#!/usr/bin/env python3

from aws_cdk import (
    aws_iam as iam,
    core
)

class InstanceProfile(core.Construct):
    '''
    Custom construct for the Instance Profile resource.
    Used to wrap the Instance Role construct.
    '''
    @property
    def profile_arn(self):
        if self._instance is None:
            self._instance = self._create_instance()
        return self._instance.attr_arn

    def attach_role(self, role):
        self._roles.append(role.role_name)

    def _create_instance(self):
        return iam.CfnInstanceProfile(self,
            self._id + "automm-cv-bench-cfn-instance-profile",
            roles=self._roles
        )

    def __init__(self, scope: core.Construct, id: str):
        super().__init__(scope, id)
        self._roles = []
        self._instance = None
        self._id = id

