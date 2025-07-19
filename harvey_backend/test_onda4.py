"""
Testes da Onda 4: Operacionalização e Deploy
Testa Docker, CI/CD, Kubernetes e operações
"""

import os
import subprocess
import json
import yaml
import requests
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.parent

class TestOnda4Operacionalizacao:
    """Testes da Onda 4: Operacionalização e Deploy"""
    
    def test_docker_compose_validation(self):
        """Testa se o docker-compose.dev.yml é válido"""
        compose_file = BASE_DIR / "docker-compose.dev.yml"
        
        # Verifica se arquivo existe
        assert compose_file.exists(), "docker-compose.dev.yml não encontrado"
        
        # Valida sintaxe YAML
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Verifica estrutura básica
        assert "version" in compose_config
        assert "services" in compose_config
        assert "volumes" in compose_config
        
        # Verifica serviços essenciais
        services = compose_config["services"]
        essential_services = ["api", "postgres", "redis", "qdrant"]
        
        for service in essential_services:
            assert service in services, f"Serviço {service} não encontrado"
        
        # Verifica configurações da API
        api_service = services["api"]
        assert "build" in api_service
        assert "ports" in api_service
        assert "depends_on" in api_service
        assert "environment" in api_service or "env_file" in api_service
        
        print("✅ Docker Compose validado com sucesso")
    
    def test_dockerfile_validation(self):
        """Testa se o Dockerfile é válido"""
        dockerfile = BASE_DIR / "Dockerfile"
        
        # Verifica se arquivo existe
        assert dockerfile.exists(), "Dockerfile não encontrado"
        
        # Lê conteúdo do Dockerfile
        with open(dockerfile, 'r') as f:
            content = f.read()
        
        # Verifica estrutura multi-stage
        assert "FROM python:3.11-slim as builder" in content
        assert "FROM python:3.11-slim as production" in content
        assert "FROM production as development" in content
        
        # Verifica configurações de segurança
        assert "USER harvey" in content
        assert "COPY --chown=harvey:harvey" in content
        
        # Verifica health check
        assert "HEALTHCHECK" in content
        
        # Verifica exposição de porta
        assert "EXPOSE 8000" in content
        
        print("✅ Dockerfile validado com sucesso")
    
    def test_github_actions_workflow(self):
        """Testa se o workflow do GitHub Actions é válido"""
        workflow_file = BASE_DIR / ".github/workflows/main_pipeline.yml"
        
        # Verifica se arquivo existe
        assert workflow_file.exists(), "Workflow do GitHub Actions não encontrado"
        
        # Valida sintaxe YAML
        with open(workflow_file, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Verifica estrutura básica
        assert "name" in workflow
        assert "on" in workflow
        assert "jobs" in workflow
        
        # Verifica jobs essenciais
        jobs = workflow["jobs"]
        essential_jobs = ["lint-and-quality", "test", "build-and-push"]
        
        for job in essential_jobs:
            assert job in jobs, f"Job {job} não encontrado"
        
        # Verifica configurações de teste
        test_job = jobs["test"]
        assert "services" in test_job
        assert "postgres" in test_job["services"]
        assert "redis" in test_job["services"]
        
        print("✅ GitHub Actions workflow validado com sucesso")
    
    def test_helm_chart_validation(self):
        """Testa se o Helm chart é válido"""
        helm_dir = BASE_DIR / "helm/harvey"
        
        # Verifica se diretório existe
        assert helm_dir.exists(), "Diretório do Helm chart não encontrado"
        
        # Verifica arquivos essenciais
        essential_files = ["Chart.yaml", "values.yaml", "templates/deployment.yaml", "templates/service.yaml"]
        
        for file in essential_files:
            file_path = helm_dir / file
            assert file_path.exists(), f"Arquivo {file} não encontrado no Helm chart"
        
        # Valida Chart.yaml
        with open(helm_dir / "Chart.yaml", 'r') as f:
            chart = yaml.safe_load(f)
        
        assert "name" in chart
        assert "version" in chart
        assert "appVersion" in chart
        
        # Valida values.yaml
        with open(helm_dir / "values.yaml", 'r') as f:
            values = yaml.safe_load(f)
        
        assert "image" in values
        assert "service" in values
        assert "resources" in values
        
        print("✅ Helm chart validado com sucesso")
    
    def test_makefile_commands(self):
        """Testa se os comandos do Makefile são válidos"""
        makefile = BASE_DIR / "Makefile"
        
        # Verifica se arquivo existe
        assert makefile.exists(), "Makefile não encontrado"
        
        # Lê conteúdo do Makefile
        with open(makefile, 'r') as f:
            content = f.read()
        
        # Verifica comandos essenciais
        essential_commands = [
            "help", "install", "test", "lint", "format", "run",
            "docker-build", "docker-compose-up", "k8s-deploy"
        ]
        
        for command in essential_commands:
            assert f"{command}:" in content, f"Comando {command} não encontrado no Makefile"
        
        # Verifica estrutura de help
        assert "help:" in content
        assert "## " in content  # Comentários de ajuda
        
        print("✅ Makefile validado com sucesso")
    
    def test_monitoring_configuration(self):
        """Testa configurações de monitoramento"""
        monitoring_dir = BASE_DIR / "monitoring"
        
        # Verifica se diretório existe
        assert monitoring_dir.exists(), "Diretório de monitoramento não encontrado"
        
        # Verifica prometheus.yml
        prometheus_file = monitoring_dir / "prometheus.yml"
        assert prometheus_file.exists(), "prometheus.yml não encontrado"
        
        with open(prometheus_file, 'r') as f:
            prometheus_config = yaml.safe_load(f)
        
        assert "global" in prometheus_config
        assert "scrape_configs" in prometheus_config
        
        # Verifica jobs de scraping
        scrape_configs = prometheus_config["scrape_configs"]
        job_names = [job["job_name"] for job in scrape_configs]
        
        assert "harvey-backend" in job_names
        assert "postgres" in job_names
        assert "redis" in job_names
        
        # Verifica alertas
        alerts_file = monitoring_dir / "alerts/harvey-backend.yml"
        assert alerts_file.exists(), "Arquivo de alertas não encontrado"
        
        with open(alerts_file, 'r') as f:
            alerts_config = yaml.safe_load(f)
        
        assert "groups" in alerts_config
        
        print("✅ Configurações de monitoramento validadas")
    
    def test_runbook_completeness(self):
        """Testa se o runbook está completo"""
        runbook_file = BASE_DIR / "docs/RUNBOOK.md"
        
        # Verifica se arquivo existe
        assert runbook_file.exists(), "RUNBOOK.md não encontrado"
        
        # Lê conteúdo do runbook
        with open(runbook_file, 'r') as f:
            content = f.read()
        
        # Verifica seções essenciais
        essential_sections = [
            "# RUNBOOK DE OPERAÇÕES",
            "## RESPOSTA A INCIDENTES",
            "SEV-1:", "SEV-2:", "SEV-3:",
            "## MONITORAMENTO E ALERTAS",
            "## PROCEDIMENTOS DE MANUTENÇÃO",
            "## PROCEDIMENTOS DE SCALE",
            "## CONTATOS DE EMERGÊNCIA"
        ]
        
        for section in essential_sections:
            assert section in content, f"Seção {section} não encontrada no runbook"
        
        # Verifica comandos de exemplo
        assert "kubectl" in content
        assert "docker" in content
        assert "helm" in content
        assert "curl" in content
        
        print("✅ Runbook validado com sucesso")
    
    def test_security_configurations(self):
        """Testa configurações de segurança"""
        # Verifica se Dockerfile usa usuário não-root
        dockerfile = BASE_DIR / "Dockerfile"
        with open(dockerfile, 'r') as f:
            dockerfile_content = f.read()
        
        assert "USER harvey" in dockerfile_content
        assert "runAsNonRoot: true" in str(BASE_DIR / "helm/harvey/values.yaml")
        
        # Verifica configurações de segurança no Helm
        values_file = BASE_DIR / "helm/harvey/values.yaml"
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)
        
        assert "securityContext" in values
        assert "networkPolicy" in values
        assert values["securityContext"]["enabled"] == True
        
        print("✅ Configurações de segurança validadas")
    
    def test_environment_files(self):
        """Testa arquivos de environment"""
        env_files = [".env.example", ".env.production"]
        
        for env_file in env_files:
            file_path = BASE_DIR / env_file
            assert file_path.exists(), f"Arquivo {env_file} não encontrado"
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Verifica variáveis essenciais
            essential_vars = [
                "DATABASE_URL", "REDIS_URL", "QDRANT_URL",
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "ENVIRONMENT", "LOG_LEVEL"
            ]
            
            for var in essential_vars:
                assert var in content, f"Variável {var} não encontrada em {env_file}"
        
        print("✅ Arquivos de environment validados")
    
    def test_scripts_executability(self):
        """Testa se scripts são executáveis"""
        scripts_dir = BASE_DIR / "scripts"
        
        # Verifica se diretório existe
        assert scripts_dir.exists(), "Diretório de scripts não encontrado"
        
        # Verifica script de setup
        setup_script = scripts_dir / "setup.sh"
        assert setup_script.exists(), "Script setup.sh não encontrado"
        
        # Verifica se é executável
        assert os.access(setup_script, os.X_OK), "Script setup.sh não é executável"
        
        print("✅ Scripts validados com sucesso")
    
    def test_ci_cd_integration(self):
        """Testa integração de CI/CD"""
        # Testa se arquivo de workflow existe e tem estrutura correta
        workflow_file = BASE_DIR / ".github/workflows/main_pipeline.yml"
        
        with open(workflow_file, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Verifica triggers
        assert "push" in workflow["on"]
        assert "pull_request" in workflow["on"]
        
        # Verifica jobs de CI/CD
        jobs = workflow["jobs"]
        
        # Job de testes
        test_job = jobs["test"]
        assert "services" in test_job
        
        # Job de build
        build_job = jobs["build-and-push"]
        assert "permissions" in build_job
        
        # Job de deploy
        deploy_jobs = [job for job in jobs.keys() if "deploy" in job]
        assert len(deploy_jobs) > 0, "Nenhum job de deploy encontrado"
        
        print("✅ Integração de CI/CD validada")
    
    def test_performance_configurations(self):
        """Testa configurações de performance"""
        # Verifica configurações no values.yaml
        values_file = BASE_DIR / "helm/harvey/values.yaml"
        
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)
        
        # Verifica autoscaling
        assert "autoscaling" in values
        assert values["autoscaling"]["enabled"] == True
        
        # Verifica recursos
        assert "resources" in values
        assert "requests" in values["resources"]
        assert "limits" in values["resources"]
        
        # Verifica health checks
        assert "healthcheck" in values
        assert "readinessProbe" in values
        assert "startupProbe" in values
        
        print("✅ Configurações de performance validadas")

def test_onda4_completa():
    """Teste integrado da Onda 4 completa"""
    tester = TestOnda4Operacionalizacao()
    
    print("\n🚀 Iniciando testes da Onda 4: Operacionalização e Deploy")
    
    # Executa todos os testes
    tester.test_docker_compose_validation()
    tester.test_dockerfile_validation()
    tester.test_github_actions_workflow()
    tester.test_helm_chart_validation()
    tester.test_makefile_commands()
    tester.test_monitoring_configuration()
    tester.test_runbook_completeness()
    tester.test_security_configurations()
    tester.test_environment_files()
    tester.test_scripts_executability()
    tester.test_ci_cd_integration()
    tester.test_performance_configurations()
    
    print("\n🎉 Todos os testes da Onda 4 passaram com sucesso!")
    print("\n📊 Resumo da validação:")
    print("  ✅ Docker Compose configurado")
    print("  ✅ Dockerfile multi-stage otimizado")
    print("  ✅ GitHub Actions CI/CD pipeline")
    print("  ✅ Helm Chart para Kubernetes")
    print("  ✅ Makefile com automação")
    print("  ✅ Monitoramento com Prometheus")
    print("  ✅ Runbook operacional completo")
    print("  ✅ Configurações de segurança")
    print("  ✅ Arquivos de environment")
    print("  ✅ Scripts executáveis")
    print("  ✅ Integração CI/CD")
    print("  ✅ Configurações de performance")
    
    print("\n🏆 Onda 4 implementada com sucesso!")
    print("  • Sistema production-ready")
    print("  • Deploy automatizado")
    print("  • Monitoramento completo")
    print("  • Operações documentadas")
    print("  • Segurança enterprise")

if __name__ == "__main__":
    test_onda4_completa()
