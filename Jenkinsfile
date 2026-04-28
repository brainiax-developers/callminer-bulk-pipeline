String packageVersion = ''

pipeline {
    agent {
        kubernetes {
            inheritFrom "terraform-python-multi"
            defaultContainer "python"
        }
    }

    // Mandatory Parameters
    parameters {
        choice(
                name: 'env',
                description: 'Deployment environment.',
                choices: 'build\ndev\ntest\nprod'
        )
        choice(
                name: 'tfAction',
                description: 'Terraform action.',
                choices: 'plan\napply\ndestroy'
        )
    }

    // Environment Variables
    environment {
        ENVIRONMENT = "${params.env}"

        CODEARTIFACT_TOKEN = sh(
                script: 'aws codeartifact get-authorization-token \
           --domain data-theverygroup \
           --domain-owner 669610644781 \
           --query authorizationToken \
           --output text \
           --region eu-west-1',
                returnStdout: true
        ).trim()
    }

    stages {

        stage('Initialising project') {
            steps {
                script {
                    currentBuild.displayName = "${currentBuild.displayName}-${params.env}-${params.tfAction}"
                    env.GIT_REPO_NAME = env.GIT_URL.replaceFirst(/^.*\/([^\/]+?).git$/, '$1')
                    packageVersion = readFile('.version')
                }
            }
        }

        stage('Validate Project Version') {
             when {
                expression {env.BRANCH_NAME != 'master'}
                expression {params.tfAction != 'destroy'}
            }
            steps {
                script {
                    validateVersion(packageVersion)
                }
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
                success { echo "Backend Successfully Initialised" }
                failure { echo "Error Initialising Backend" }
            }
        }

        stage('Terraform Targeted Plan - ECR + SSM') {
            steps {
                container('terraform') {
                    script {
                        tfDo('plan', params.env, params.tfAction, packageVersion, 'module.ecr,module.ssm_param_ecr_repo_url')
                    }
                }
            }
            post {
                success { echo "ECR + SSM Plan Successful" }
                failure { echo "ECR + SSM Plan Failure" }
            }
        }

        stage('Terraform Targeted Apply - ECR + SSM') {
            when {
                expression {params.tfAction == 'apply'}
            }
            steps {
                container('terraform') {
                    script {
                        tfDo('apply', params.env, params.tfAction, packageVersion, 'module.ecr,module.ssm_param_ecr_repo_url')
                    }
                }
            }
        }

        stage('Build and Push Image to Build Account') {
            when {
                allOf {
                    expression {params.env == 'build'}
                    expression {params.tfAction == 'apply'}
                }
            }
            steps {
                script {
                    String account = 'nonprod'
                    if (params.env == 'prod') {
                        account = 'prod'
                    }
                    awsCodeBuild (
                        projectName: 'build-cip-ci-codebuild-basic-project',
                        buildSpecFile: 'buildspec-push.yaml',
                        credentialsType: 'keys',
                        downloadArtifacts: 'false',
                        region: 'eu-west-1',
                        sourceControlType: 'jenkins',
                        sourceLocationOverride: "build-cip-ci-codebuild-assets-s3/${currentBuild.fullProjectName}/${currentBuild.id}/workspace.zip",
                        sourceTypeOverride: 'S3',
                        workspaceSubdir: '',
                        envVariables: "[ { VERSION, ${packageVersion} } ]"
                    )
                }
            }
            post {
                success { echo "Build and Push to Build Account Successful" }
                failure { echo "Build and Push to Build Account Failure" }
            }
        }

        stage('Pull Image from Build Account and Push to Env') {
            when {
                allOf {
                    expression {params.env != 'build'}
                    expression {params.tfAction == 'apply'}
                }
            }
            steps {
                script {
                    String account = 'prod'
                    if (params.env != 'prod') {
                        account = 'nonprod'
                    }
                    awsCodeBuild (
                        projectName: 'build-cip-ci-codebuild-basic-project',
                        buildSpecFile: 'buildspec-pull.yaml',
                        credentialsType: 'keys',
                        downloadArtifacts: 'false',
                        region: 'eu-west-1',
                        sourceControlType: 'jenkins',
                        sourceLocationOverride: "build-cip-ci-codebuild-assets-s3/${currentBuild.fullProjectName}/${currentBuild.id}/workspace.zip",
                        sourceTypeOverride: 'S3',
                        workspaceSubdir: '',
                        envVariables: "[{ ENVIRONMENT, ${params.env}}, { ACCOUNT, ${account}}, { VERSION, ${packageVersion} } ]"
                    )
                }
            }
            post {
                success { echo "Pull and Push to ${params.env} Successful" }
                failure { echo "Pull and Push to ${params.env} Failure" }
            }
        }

        stage('Terraform Plan') {
            steps {
                container('terraform') {
                    script {
                        tfDo('plan', params.env, params.tfAction, packageVersion)
                    }
                }
            }
            post {
                success { echo "Plan Successful" }
                failure { echo "Plan Failure" }
            }
        }

        stage('Terraform Apply/Destroy') {
            when {
                expression { params.tfAction == 'apply' || params.tfAction == 'destroy' }
            }
            steps {
                container('terraform') {
                    script {
                        timeout(time: 10, unit: 'MINUTES') { input message: "This will apply the changes in ${params.env} - Have you reviewed the Planning Stage?" }
                        tfDo(params.tfAction, params.env, params.tfAction, packageVersion)
                    }
                }
            }
            post {
                success { echo "Apply Successful" }
                failure { echo "Apply Failure" }
            }
        }

        stage('Tag Release') {
            when {
                allOf {
                    expression {params.env == 'prod'}
                    expression {params.tfAction == 'apply'}
                    expression {env.BRANCH_NAME == 'master'}
                }
            }
            steps {
                    sshagent (credentials: ['build/jenkins/gitlab-private-key-alt']) {
                            tagReleaseCommitInGit(packageVersion)
                    } 
                }
            }

    }
}


def tfDo(String terraformAction, String deployToEnvironment, String planAction='', String packageVersion='', String target='') {
    echo "tfDo - Environment : ${deployToEnvironment}"
    echo "tfDo - Action : ${terraformAction}"
    echo "tfDo - Plan Action : ${planAction}"
    echo "tfDo - Package Version : ${packageVersion}"
    echo "tfDo - Target : ${target}"
    String envAccount = "prod"
    String terraformDir = 'tf'
    String configPrefix = 'config'
    if (deployToEnvironment == 'build') {
        terraformDir = 'tf/deploy-build'
        configPrefix = '../config'
    }
    if (deployToEnvironment != "prod") {
        envAccount = "nonprod"
    }
    String targetFlag = target ? target.split(',').collect { "-target=${it.trim()}" }.join(' ') : ""
    sh "ssh-keyscan git.tech.theverygroup.com >> ~/.ssh/known_hosts"
    dir(terraformDir) {
        sshagent (credentials: ['build/jenkins/gitlab-private-key-alt']) {
            withAWS(useNode: true){
                if (terraformAction == 'init') {
                    sh """
                        terraform init -reconfigure \
                            -backend-config=${configPrefix}/backend.common.conf \
                            -backend-config=${configPrefix}/${deployToEnvironment}/backend.conf
                        """
                } else if (terraformAction == 'plan') {
                    if (planAction == 'apply' || planAction == 'plan'){
                        sh "terraform plan -var-file=./${configPrefix}/${deployToEnvironment}/vars.tfvars -var=\"created_by=${env.GIT_REPO_NAME}\" -var=\"image_version=${packageVersion}\" ${targetFlag} -out=tfplan"
                    }
                    else if (planAction == 'destroy'){
                        sh "terraform plan -destroy -var-file=./${configPrefix}/${deployToEnvironment}/vars.tfvars -var=\"created_by=${env.GIT_REPO_NAME}\" -var=\"image_version=${packageVersion}\" ${targetFlag} -out=deleteplan"
                    }
                } else if (terraformAction == 'apply') {
                    sh "terraform apply tfplan"
                } else if (terraformAction == 'destroy') {
                    sh "terraform apply deleteplan"
                }
            }
        }
    }
}

def validateVersion(String version) {
    sshagent (credentials: ['build/jenkins/gitlab-private-key-alt']) {
        if (!version?.trim()) {
            error("Version value is required")
        }

        sh "git fetch --tags --force"
        def existingTag = sh(
                script: "git tag -l v${version}",
                returnStdout: true
        ).trim()

        if (existingTag) {
            error("Version v${version} already exists as a Git tag")
        }
    }
}

def tagReleaseCommitInGit(String packageVersion) {
    String releaseCommitHash = sh(script: "git rev-parse HEAD", returnStdout: true).trim()
    String versionTag = "v${packageVersion}"
    sh """#!/bin/bash
        git tag -a ${versionTag} ${releaseCommitHash} -m '[jenkins version tag]'
        git push origin ${versionTag}
    """
}
