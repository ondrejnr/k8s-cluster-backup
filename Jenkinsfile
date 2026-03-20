pipeline {
  agent { label 'k8s-agent' }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Verify') {
      steps {
        sh 'pwd'
        sh 'ls -la'
        sh 'git rev-parse --short HEAD'
      }
    }
  }
}
