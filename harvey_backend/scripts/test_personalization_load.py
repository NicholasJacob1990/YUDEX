#!/usr/bin/env python3
"""
Script de teste de carga para sistema de personalização por centroides
Avalia performance e consistência do sistema sob diferentes cargas
"""

import asyncio
import time
import numpy as np
import statistics
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar caminho do projeto
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.personalization import get_personalizer
from app.core.rag_bridge import get_rag_bridge
from scripts.calculate_centroids import CentroidCalculator

class PersonalizationLoadTester:
    """Testador de carga para sistema de personalização"""
    
    def __init__(self):
        self.personalizer = get_personalizer()
        self.rag_bridge = get_rag_bridge()
        self.calculator = CentroidCalculator()
        
        # Métricas
        self.metrics = {
            "centroid_retrieval": [],
            "personalization_apply": [],
            "federated_search": [],
            "centroid_calculation": [],
            "errors": []
        }
    
    def generate_test_data(self, num_tenants: int = 5, num_queries: int = 100) -> Dict[str, Any]:
        """Gera dados de teste"""
        
        # Tenants de teste
        tenants = [f"tenant_{i}" for i in range(num_tenants)]
        
        # Queries de teste
        test_queries = [
            "Contrato de locação comercial com garantia",
            "Processo trabalhista por horas extras",
            "Imposto sobre produtos industrializados",
            "Divórcio consensual com partilha de bens",
            "Crime de estelionato em operação financeira",
            "Licitação pública para obras municipais",
            "Mandado de segurança contra ato administrativo",
            "Recuperação judicial de empresa privada",
            "Sucessão hereditária em inventário",
            "Responsabilidade civil por danos morais"
        ]
        
        # Gerar combinações aleatórias
        queries = []
        for i in range(num_queries):
            tenant = np.random.choice(tenants)
            query = np.random.choice(test_queries)
            alpha = np.random.uniform(0.1, 0.8)
            
            queries.append({
                "id": i,
                "tenant_id": tenant,
                "query": query,
                "alpha": alpha
            })
        
        return {
            "tenants": tenants,
            "queries": queries,
            "test_queries": test_queries
        }
    
    async def test_centroid_retrieval(self, tenant_id: str, tag: str) -> Dict[str, Any]:
        """Testa recuperação de centroide"""
        start_time = time.time()
        
        try:
            centroid = await self.personalizer.get_centroid(tenant_id, tag)
            end_time = time.time()
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "centroid_found": centroid is not None,
                "centroid_dimension": len(centroid) if centroid is not None else 0
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "error": str(e)
            }
    
    async def test_personalization_apply(self, tenant_id: str, query: str, alpha: float) -> Dict[str, Any]:
        """Testa aplicação de personalização"""
        start_time = time.time()
        
        try:
            # Gerar vetor de query simulado
            query_vector = np.random.rand(768)
            query_vector = query_vector / np.linalg.norm(query_vector)
            
            # Aplicar personalização
            result = await self.personalizer.apply_personalization(
                query_vector=query_vector,
                tenant_id=tenant_id,
                query=query,
                alpha=alpha
            )
            
            end_time = time.time()
            
            # Calcular similaridade
            similarity = np.dot(query_vector, result) if result is not None else 0
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "similarity": float(similarity),
                "vector_modified": not np.allclose(query_vector, result, atol=1e-6)
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "error": str(e)
            }
    
    async def test_federated_search(self, tenant_id: str, query: str, alpha: float) -> Dict[str, Any]:
        """Testa busca federada com personalização"""
        start_time = time.time()
        
        try:
            # Busca com personalização
            results_personalized = await self.rag_bridge.federated_search(
                query=query,
                tenant_id=tenant_id,
                k_total=10,
                personalization_alpha=alpha,
                enable_personalization=True
            )
            
            # Busca sem personalização
            results_standard = await self.rag_bridge.federated_search(
                query=query,
                tenant_id=tenant_id,
                k_total=10,
                enable_personalization=False
            )
            
            end_time = time.time()
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "personalized_results": len(results_personalized),
                "standard_results": len(results_standard),
                "results_differ": results_personalized != results_standard
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "error": str(e)
            }
    
    async def test_centroid_calculation(self, tenant_id: str) -> Dict[str, Any]:
        """Testa cálculo de centroides"""
        start_time = time.time()
        
        try:
            results = await self.calculator.calculate_and_store_centroids(tenant_id)
            end_time = time.time()
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "tags_processed": total_count,
                "tags_successful": success_count,
                "success_rate": success_count / total_count if total_count > 0 else 0
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "error": str(e)
            }
    
    async def run_concurrent_tests(self, test_data: Dict[str, Any], concurrency: int = 10) -> Dict[str, Any]:
        """Executa testes concorrentes"""
        
        logger.info(f"Iniciando testes de carga com concorrência {concurrency}")
        
        # Semáforo para controlar concorrência
        semaphore = asyncio.Semaphore(concurrency)
        
        async def run_single_test(query_data: Dict[str, Any]):
            async with semaphore:
                tenant_id = query_data["tenant_id"]
                query = query_data["query"]
                alpha = query_data["alpha"]
                
                # Executar testes
                results = {}
                
                # Teste 1: Recuperação de centroide
                tag = await self.personalizer.infer_query_tag(query)
                results["centroid_retrieval"] = await self.test_centroid_retrieval(tenant_id, tag)
                
                # Teste 2: Aplicação de personalização
                results["personalization_apply"] = await self.test_personalization_apply(tenant_id, query, alpha)
                
                # Teste 3: Busca federada (mais pesado)
                results["federated_search"] = await self.test_federated_search(tenant_id, query, alpha)
                
                return {
                    "query_id": query_data["id"],
                    "tenant_id": tenant_id,
                    "query": query,
                    "alpha": alpha,
                    "results": results
                }
        
        # Executar todos os testes
        start_time = time.time()
        
        tasks = [run_single_test(query_data) for query_data in test_data["queries"]]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Processar resultados
        successful_tests = []
        failed_tests = []
        
        for result in test_results:
            if isinstance(result, Exception):
                failed_tests.append({"error": str(result)})
            else:
                successful_tests.append(result)
        
        # Calcular métricas
        metrics = self.calculate_metrics(successful_tests)
        
        return {
            "test_summary": {
                "total_tests": len(test_data["queries"]),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "success_rate": len(successful_tests) / len(test_data["queries"]),
                "total_duration": end_time - start_time,
                "average_duration_per_test": (end_time - start_time) / len(test_data["queries"])
            },
            "metrics": metrics,
            "failed_tests": failed_tests[:10]  # Apenas os primeiros 10 erros
        }
    
    def calculate_metrics(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula métricas de performance"""
        
        metrics = {
            "centroid_retrieval": [],
            "personalization_apply": [],
            "federated_search": []
        }
        
        # Coletar durações
        for test_result in test_results:
            results = test_result.get("results", {})
            
            for metric_name in metrics.keys():
                if metric_name in results and results[metric_name].get("success"):
                    metrics[metric_name].append(results[metric_name]["duration"])
        
        # Calcular estatísticas
        stats = {}
        for metric_name, durations in metrics.items():
            if durations:
                stats[metric_name] = {
                    "count": len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "mean": statistics.mean(durations),
                    "median": statistics.median(durations),
                    "std": statistics.stdev(durations) if len(durations) > 1 else 0,
                    "p95": np.percentile(durations, 95),
                    "p99": np.percentile(durations, 99)
                }
            else:
                stats[metric_name] = {"count": 0}
        
        return stats
    
    async def test_centroid_calculation_load(self, tenants: List[str]) -> Dict[str, Any]:
        """Testa cálculo de centroides sob carga"""
        
        logger.info(f"Testando cálculo de centroides para {len(tenants)} tenants")
        
        start_time = time.time()
        
        # Executar cálculo para todos os tenants
        results = await self.calculator.calculate_all_tenants(tenants)
        
        end_time = time.time()
        
        # Processar resultados
        successful_tenants = sum(1 for tenant_results in results.values() 
                               if isinstance(tenant_results, dict) and 'error' not in tenant_results)
        
        return {
            "total_tenants": len(tenants),
            "successful_tenants": successful_tenants,
            "failed_tenants": len(tenants) - successful_tenants,
            "success_rate": successful_tenants / len(tenants),
            "total_duration": end_time - start_time,
            "average_duration_per_tenant": (end_time - start_time) / len(tenants),
            "results": results
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Gera relatório de teste"""
        
        report = []
        report.append("=" * 60)
        report.append("RELATÓRIO DE TESTE DE CARGA - PERSONALIZAÇÃO")
        report.append("=" * 60)
        
        # Resumo geral
        summary = results["test_summary"]
        report.append(f"\nRESUMO GERAL:")
        report.append(f"  Total de testes: {summary['total_tests']}")
        report.append(f"  Testes bem-sucedidos: {summary['successful_tests']}")
        report.append(f"  Testes falhados: {summary['failed_tests']}")
        report.append(f"  Taxa de sucesso: {summary['success_rate']:.2%}")
        report.append(f"  Duração total: {summary['total_duration']:.2f}s")
        report.append(f"  Duração média por teste: {summary['average_duration_per_test']:.3f}s")
        
        # Métricas de performance
        metrics = results["metrics"]
        report.append(f"\nMÉTRICAS DE PERFORMANCE:")
        
        for metric_name, stats in metrics.items():
            if stats["count"] > 0:
                report.append(f"\n  {metric_name.replace('_', ' ').title()}:")
                report.append(f"    Contagem: {stats['count']}")
                report.append(f"    Mínimo: {stats['min']:.3f}s")
                report.append(f"    Máximo: {stats['max']:.3f}s")
                report.append(f"    Média: {stats['mean']:.3f}s")
                report.append(f"    Mediana: {stats['median']:.3f}s")
                report.append(f"    Desvio padrão: {stats['std']:.3f}s")
                report.append(f"    P95: {stats['p95']:.3f}s")
                report.append(f"    P99: {stats['p99']:.3f}s")
        
        # Erros
        if results.get("failed_tests"):
            report.append(f"\nERROS (primeiros 10):")
            for i, error in enumerate(results["failed_tests"][:10]):
                report.append(f"  {i+1}. {error.get('error', 'Erro desconhecido')}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


async def main():
    """Função principal"""
    
    parser = argparse.ArgumentParser(description="Teste de carga para personalização")
    parser.add_argument("--tenants", type=int, default=5, help="Número de tenants")
    parser.add_argument("--queries", type=int, default=100, help="Número de queries")
    parser.add_argument("--concurrency", type=int, default=10, help="Nível de concorrência")
    parser.add_argument("--output", type=str, help="Arquivo de saída para relatório")
    parser.add_argument("--test-centroids", action="store_true", help="Testar cálculo de centroides")
    
    args = parser.parse_args()
    
    # Criar testador
    tester = PersonalizationLoadTester()
    
    # Gerar dados de teste
    test_data = tester.generate_test_data(
        num_tenants=args.tenants,
        num_queries=args.queries
    )
    
    logger.info(f"Dados de teste gerados: {args.tenants} tenants, {args.queries} queries")
    
    # Executar testes principais
    results = await tester.run_concurrent_tests(test_data, args.concurrency)
    
    # Testar cálculo de centroides se solicitado
    if args.test_centroids:
        logger.info("Testando cálculo de centroides...")
        centroid_results = await tester.test_centroid_calculation_load(test_data["tenants"])
        results["centroid_calculation"] = centroid_results
    
    # Gerar relatório
    report = tester.generate_report(results)
    
    # Salvar ou imprimir relatório
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        logger.info(f"Relatório salvo em: {args.output}")
    else:
        print(report)
    
    # Salvar dados detalhados em JSON
    json_output = args.output.replace('.txt', '.json') if args.output else 'load_test_results.json'
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Dados detalhados salvos em: {json_output}")


if __name__ == "__main__":
    asyncio.run(main())
