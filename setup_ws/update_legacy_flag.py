from azureml.core import Workspace
# from azureml.core.authentication import InteractiveLoginAuthentication
# interactive_auth = InteractiveLoginAuthentication(tenant_id="72f988bf-86f1-41af-91ab-2d7cd011db47")
# ws = Workspace(subscription_id=subscription_id, 
#               resource_group=resource_group,
#               workspace_name=workspace_name,
#               auth=interactive_auth)

ws = Workspace.from_config()

ws.update(v1_legacy_mode=False)