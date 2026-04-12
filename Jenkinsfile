pipeline {
    agent {
        kubernetes {
            inheritFrom "terraform-python-multi"
            defaultContainer "python"
        }
    }

    parameters {
        choice(
            name: 'env',
            description: 'Deployment environment.',
            choices: 'dev\ntest\nprod'
        )
        choice(
            name: 'tfAction',
            description: 'Terraform action.',
            choices: 'plan\napply\ndestroy'
        )
    }

    environment {
        ENVIRONMENT = "${params.env}"
    }

    stages {
        stage('Initialising project') {
            steps {
                script {
                    currentBuild.displayName = "${currentBuild.displayName}-${params.env}-${params.tfAction}"
                    env.GIT_REPO_NAME = env.GIT_URL.replaceFirst(/^.*\/([^\/]+?).git$/, '$1')
                }
            }
        }

        stage('Unit Tests') {
            steps {
                container('python') {
                    sh 'python -m unittest discover -s tests -p "test*.py" -v'
                }
            }
            post {
                success { echo "Unit tests passed" }
                failure { echo "Unit tests failed" }
            }
        }

        stage('Initialising Backend') {
            steps {
                container('terraform') {
                    script {
                        tfDo('init', params.env)
                    }
                }
            }
            post {
                success { echo "Backend initialised" }
                failure { echo "Backend initialisation failed" }
            }
        }

        stage('Terraform Validate') {
            steps {
                container('terraform') {
                    script {
                        tfDo('validate', params.env)
                    }
                }
            }
            post {
                success { echo "Terraform validate passed" }
                failure { echo "Terraform validate failed" }
            }
        }

        stage('Terraform Plan') {
            steps {
                container('terraform') {
                    script {
                        tfDo('plan', params.env, params.tfAction)
                    }
                }
            }
            post {
                success { echo "Terraform plan completed" }
                failure { echo "Terraform plan failed" }
            }
        }

        stage('Terraform Apply/Destroy') {
            when {
                expression { params.tfAction == 'apply' || params.tfAction == 'destroy' }
            }
            steps {
                container('terraform') {
                    script {
                        timeout(time: 10, unit: 'MINUTES') {
                            input message: "This will ${params.tfAction} resources in ${params.env}. Proceed?"
                        }
                        tfDo(params.tfAction, params.env, params.tfAction)
                    }
                }
            }
        }
    }
}

def tfDo(String terraformAction, String deployToEnvironment, String planAction='') {
    echo "tfDo - Environment : ${deployToEnvironment}"
    echo "tfDo - Action : ${terraformAction}"
    echo "tfDo - Plan Action : ${planAction}"

    dir('tf') {
        withAWS(useNode: true) {
            if (terraformAction == 'init') {
                sh """
                    terraform init -reconfigure \
                        -backend-config=config/backend.common.conf \
                        -backend-config=config/${deployToEnvironment}/backend.conf
                """
            } else if (terraformAction == 'validate') {
                sh 'terraform validate'
            } else if (terraformAction == 'plan') {
                if (planAction == 'destroy') {
                    sh "terraform plan -destroy -var-file=./config/${deployToEnvironment}/vars.tfvars -var=\"created_by=${env.GIT_REPO_NAME}\" -out=deleteplan"
                } else {
                    sh "terraform plan -var-file=./config/${deployToEnvironment}/vars.tfvars -var=\"created_by=${env.GIT_REPO_NAME}\" -out=tfplan"
                }
            } else if (terraformAction == 'apply') {
                sh 'terraform apply tfplan'
            } else if (terraformAction == 'destroy') {
                sh 'terraform apply deleteplan'
            }
        }
    }
}
