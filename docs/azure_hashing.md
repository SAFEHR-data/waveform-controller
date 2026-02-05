# Setting up Azure + Hashing in Dev and Production

# Create and configure Azure key vaults

Azure key vaults for dev and prod already exist. Ask your team-mates how to find the details for these.

For each, there is an Azure service principal (aka. machine account) that can read/write secrets to
the key vault.

> ![CAUTION]
> Never use the production key vault credentials anywhere except on the production machines!
> The dev key vault credentials can be used for testing on your dev machine, testing
> on GitHub Actions, etc, but should still be kept safe.
> Also, there is no need to store the actual secret keys themselves outside of the key vaults,
> that's what the key vaults are for!

# Configure hasher
The hasher needs to be given the service principal details so it can create/obtain the
secrets. It also needs to know the name of the manually-created secret (see next section for more details).

See [hasher example config](../config.EXAMPLE/hasher.env.EXAMPLE) for detailed description of required env vars.

# Manual Azure config

There is a one-off (per key vault) step that needs to be performed manually.

First, install the Azure CLI tools in the usual way for your OS.

Log in using the service principal.
Do not include password on command line; let it prompt you and then paste it in.
```
az login --service-principal --username <APP_ID> --tenant <TENANT_ID>
```

Now you can run commands to inspect the existing setup:
```
# show all keyvaults
az keyvault list

# Show keyvault details (not secrets). name is "name" key from previous command
az keyvault show --name <keyvault_name>

# list all secrets in keyvault
az keyvault secret list --vault-name <keyvault_name>
```
As per [PIXL instructions](https://github.com/SAFEHR-data/PIXL/blob/main/docs/setup/azure-keyvault.md#step-4),
you need to manually create a secret project-level key:
```
az keyvault secret set --vault-name <keyvault_name> --name <secret_name> --value <secret_value>
```
Note that you can choose the name of this secret (`<secret_name>` above), and its name (NOT its value)
should be placed in the config env var `AZURE_KEY_VAULT_SECRET_NAME`

In addition, the PIXL hasher automatically creates a secret named after the "project slug" that you pass
in, the first time that you request a hash using that project slug.
