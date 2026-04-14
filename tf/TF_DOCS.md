[//]: # (BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK)



## Requirements

| Name | Version |
|------|---------|
| terraform | >=1.6.2 |
| aws | >=5.22.0 |

## Providers

| Name | Version |
|------|---------|
| aws | 6.26.0 |
| aws.build | 6.26.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| ecr | git@git.tech.theverygroup.com:data/pipelines/modules/terraform/ecr.git | v1.1.1 |
| label | git@git.tech.theverygroup.com:pe/public/tf-modules/pe-tf-module-tag.git | v1.6.0 |
| lambda | git@git.tech.theverygroup.com:data/pipelines/modules/terraform/python-lambda.git | v3.0.0 |
| ssm\_param\_ecr\_repo\_url | git@git.tech.theverygroup.com:data/platform/modules/terraform/parameter-store.git//modules/ssm_parameter_put | v1.2 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | The runtime environment | `string` | n/a | yes |
| region | The region | `string` | `"eu-west-1"` | no |
| business\_capability\_l0 | The Business Capability Level 0 | `string` | n/a | yes |
| business\_capability\_l1 | The Business Capability Level 1 | `string` | n/a | yes |
| service\_tier | The Service Tier | `string` | n/a | yes |
| data\_classification | The Data Classification | `string` | n/a | yes |
| created\_by | The created by repo | `string` | n/a | yes |
| service\_owner | The Service Owner | `string` | n/a | yes |
| service | The Service Name | `string` | n/a | yes |
| project | The project the work belongs to | `string` | `"lakehouse"` | no |
| category | The category of the work | `string` | `"callminer-bulk-pipeline"` | no |
| image\_version | The version number of the ECR image for the Lambda | `string` | n/a | yes |

## Resources

| Name | Type |
|------|------|

## Outputs

No outputs.

[//]: # (END OF PRE-COMMIT-TERRAFORM DOCS HOOK)