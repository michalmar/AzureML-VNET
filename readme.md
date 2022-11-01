# AzureML Secured Workspace with Private Link


based on: https://learn.microsoft.com/en-us/azure/machine-learning/how-to-secure-online-endpoint?tabs=cli%2Cmodel#end-to-end-example

arch:
![arch](https://learn.microsoft.com/en-us/azure/machine-learning/media/how-to-secure-online-endpoint/endpoint-network-isolation-diagram.png)

## Steps

1. clone repo with scripts
```sh

git clone https://github.com/Azure/azureml-examples
rm -rf azureml-examples/.git 
cd azureml-examples/cli

```
1. login to Azure CLI

```sh
az login --tenant 9fe3aa9b-55d5-419c-9e8d-9287463a11c6 --use-device-code
az account set --subscription a90550ee-2b3c-4802-acef-79472a9b6510
```


1. create workspace in azure
```sh
# SUFFIX will be used as resource name suffix in created workspace and related resources
export SUFFIX="888"
export SUBSCRIPTION="a90550ee-2b3c-4802-acef-79472a9b6510"
export RESOURCE_GROUP="rg-mlw-secure"
export LOCATION="westeurope"

export WORKSPACE=mlw-$SUFFIX
export ACR_NAME=cr$SUFFIX


# provide a unique name for the endpoint
export ENDPOINT_NAME=mlwonlinesecure$SUFFIX

# name of the image that will be built for this sample and pushed into acr - no need to change this
export IMAGE_NAME="img"

# Yaml files that will be used to create endpoint and deployment. These are relative to azureml-examples/cli/ directory. Do not change these
export ENDPOINT_FILE_PATH="endpoints/online/managed/vnet/sample/endpoint.yml"
export DEPLOYMENT_FILE_PATH="endpoints/online/managed/vnet/sample/blue-deployment-vnet.yml"
export SAMPLE_REQUEST_PATH="endpoints/online/managed/vnet/sample/sample-request.json"
export ENV_DIR_PATH="endpoints/online/managed/vnet/sample/environment"

az configure --defaults group=$RESOURCE_GROUP workspace=$WORKSPACE

az group create --name rg-mlw-secure --location westeurope
az deployment group create --template-file ./setup_ws/main.bicep --parameters suffix=$SUFFIX

```
1. Create the virtual machine jump box, in the same vnet and subnet
```sh
az vm create --name jump-vm --vnet-name vnet-$SUFFIX --subnet snet-scoring --image UbuntuLTS --admin-username mma --admin-password <your-new-password>
```

1. SSH to VM `ssh mma@51.144.54.87` (public IP address)

```sh

# SUFFIX will be used as resource name suffix in created workspace and related resources
export SUFFIX="888"
export SUBSCRIPTION="a90550ee-2b3c-4802-acef-79472a9b6510"
export RESOURCE_GROUP="rg-mlw-secure"
export LOCATION="westeurope"

export WORKSPACE=mlw-$SUFFIX
export ACR_NAME=cr$SUFFIX


# provide a unique name for the endpoint
export ENDPOINT_NAME=mlwonlinesecure$SUFFIX

# name of the image that will be built for this sample and pushed into acr - no need to change this
export IMAGE_NAME="img"

# Yaml files that will be used to create endpoint and deployment. These are relative to azureml-examples/cli/ directory. Do not change these
export ENDPOINT_FILE_PATH="endpoints/online/managed/vnet/sample/endpoint.yml"
export DEPLOYMENT_FILE_PATH="endpoints/online/managed/vnet/sample/blue-deployment-vnet.yml"
export SAMPLE_REQUEST_PATH="endpoints/online/managed/vnet/sample/sample-request.json"
export ENV_DIR_PATH="endpoints/online/managed/vnet/sample/environment"

sudo mkdir -p /home/samples; sudo git clone -b main --depth 1 https://github.com/Azure/azureml-examples.git /home/samples/azureml-examples
sudo mv /home/samples/azureml-examples/cli/endpoints/ /home/samples/
sudo rm -rf /home/samples/azureml-examples/


# Navigate to the samples
cd /home/samples/$ENV_DIR_PATH

# login to acr. Optionally, to avoid using sudo, complete the docker post install steps: https://docs.docker.com/engine/install/linux-postinstall/
sudo az acr login -n "$ACR_NAME"
# Build the docker image with the sample docker file
sudo docker build -t "$ACR_NAME.azurecr.io/repo/$IMAGE_NAME":v1 .
# push the image to the ACR
sudo docker push "$ACR_NAME.azurecr.io/repo/$IMAGE_NAME":v1
# check if the image exists in acr
az acr repository show -n "$ACR_NAME" --repository "repo/$IMAGE_NAME"



```

### Update the WS - set lega

Go back to from the JUMP VM to Codespaces:
run Python and execute:

```python
from azureml.core import Workspace
ws = Workspace.from_config()
ws.update(v1_legacy_mode=False)
```
> Important: Note that it takes about 30 minutes to an hour or more for changing v1_legacy_mode parameter from true to false to be reflected in the workspace. Therefore, if you set the parameter to false but receive an error that the parameter is true in a subsequent operation, please try after a few more minutes.

Check the workspace (eventhough it states `False`, you need to wait 30min - see above):

```python
details = ws.get_details()
details["v1LegacyMode"]
```

If you fail to do so, you might get errors like:

```
(UserError) The workspace has been configured by your administrator to disallow this request (V1LegacyMode == true).
Code: UserError
...
...
```

### Create a secured managed online endpoint

```sh
cd /home/samples/

# create endpoint
az ml online-endpoint create --name $ENDPOINT_NAME -f $ENDPOINT_FILE_PATH --set public_network_access="disabled"

# create deployment in managed vnet
az ml online-deployment create --name blue --endpoint $ENDPOINT_NAME -f $DEPLOYMENT_FILE_PATH --all-traffic --set environment.image="$ACR_NAME.azurecr.io/repo/$IMAGE_NAME:v1" egress_public_network_access="disabled"
```
> Note: if you face errors due to the `V1LegacyMode == true`, see previous section.



Test the Endpoint:
```sh
# Try scoring using the CLI
az ml online-endpoint invoke --name $ENDPOINT_NAME --request-file $SAMPLE_REQUEST_PATH

# Try scoring using curl
ENDPOINT_KEY=$(az ml online-endpoint get-credentials -n $ENDPOINT_NAME -o tsv --query primaryKey)
SCORING_URI=$(az ml online-endpoint show -n $ENDPOINT_NAME -o tsv --query scoring_uri)
curl --request POST "$SCORING_URI" --header "Authorization: Bearer $ENDPOINT_KEY" --header 'Content-Type: application/json' --data @$SAMPLE_REQUEST_PATH
```