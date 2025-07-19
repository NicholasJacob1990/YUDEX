"""
Sistema de Avaliação de Qualidade para Agentes
Implementa golden dataset, métricas e avaliação automatizada
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Tipos de métricas de avaliação"""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    LEGAL_COMPLIANCE = "legal_compliance"
    RESPONSE_TIME = "response_time"
    COHERENCE = "coherence"
    CITATION_QUALITY = "citation_quality"

@dataclass
class GoldenSample:
    """Amostra do golden dataset"""
    id: str
    input_prompt: str
    expected_output: str
    category: str
    difficulty: str  # easy, medium, hard
    legal_area: str  # civil, penal, administrativo, etc.
    expected_tools: List[str]  # ferramentas que deveriam ser usadas
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        # Gera hash único se não fornecido
        if not self.id:
            content = f"{self.input_prompt}{self.expected_output}{self.category}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:8]

@dataclass
class EvaluationResult:
    """Resultado de uma avaliação"""
    sample_id: str
    agent_output: str
    metrics: Dict[MetricType, float]
    execution_time: float
    tools_used: List[str]
    timestamp: datetime
    error: Optional[str] = None

class GoldenDataset:
    """Dataset de teste com exemplos de referência"""
    
    def __init__(self):
        self.samples: List[GoldenSample] = []
        self._load_builtin_samples()
    
    def _load_builtin_samples(self):
        """Carrega amostras built-in para teste"""
        
        # Amostra 1: Jurisprudência sobre contratos administrativos
        self.samples.append(GoldenSample(
            id="juris_001",
            input_prompt="Preciso de jurisprudência recente do STJ sobre rescisão de contratos administrativos por inexecução",
            expected_output="Com base na jurisprudência recente, o STJ entende que a rescisão de contratos administrativos por inexecução deve observar os princípios do contraditório e ampla defesa...",
            category="jurisprudencia",
            difficulty="medium",
            legal_area="administrativo",
            expected_tools=["buscar_jurisprudencia_recente"],
            metadata={"tribunal": "STJ", "tema": "contratos administrativos"}
        ))
        
        # Amostra 2: Cálculo de valor da causa
        self.samples.append(GoldenSample(
            id="calc_001",
            input_prompt="Qual seria o valor da causa para uma ação de indenização por danos morais no valor de R$ 50.000?",
            expected_output="Para uma ação de indenização por danos morais com valor pretendido de R$ 50.000, o valor da causa deve corresponder ao valor da indenização pleiteada...",
            category="calculo",
            difficulty="easy",
            legal_area="civil",
            expected_tools=["calcular_valor_causa"],
            metadata={"tipo_acao": "indenizacao", "valor": 50000}
        ))
        
        # Amostra 3: Validação de fundamentação legal
        self.samples.append(GoldenSample(
            id="valid_001",
            input_prompt="Valide a fundamentação legal deste texto: 'O contrato deve ser rescindido com base no art. 78 da Lei 8.666/93'",
            expected_output="A fundamentação apresentada está correta. O art. 78 da Lei 8.666/93 trata efetivamente das hipóteses de rescisão contratual...",
            category="validacao",
            difficulty="medium",
            legal_area="administrativo",
            expected_tools=["validar_fundamentacao_legal", "buscar_legislacao_atualizada"],
            metadata={"norma": "Lei 8.666/93", "artigo": "78"}
        ))
        
        # Amostra 4: Busca de documento interno
        self.samples.append(GoldenSample(
            id="doc_001",
            input_prompt="Busque o documento interno DOC_TEMPLATE_001 para usar como referência",
            expected_output="O documento DOC_TEMPLATE_001 contém o modelo padrão para petições iniciais...",
            category="documento",
            difficulty="easy",
            legal_area="geral",
            expected_tools=["buscar_documento_interno"],
            metadata={"doc_id": "DOC_TEMPLATE_001"}
        ))
        
        # Amostra 5: Legislação atualizada
        self.samples.append(GoldenSample(
            id="leg_001",
            input_prompt="Preciso da redação atualizada do art. 421 do Código Civil sobre função social dos contratos",
            expected_output="O art. 421 do Código Civil estabelece que a liberdade contratual deve ser exercida nos limites da função social do contrato...",
            category="legislacao",
            difficulty="medium",
            legal_area="civil",
            expected_tools=["buscar_legislacao_atualizada"],
            metadata={"norma": "Código Civil", "artigo": "421"}
        ))
        
        # Amostra 6: Caso complexo - múltiplas ferramentas
        self.samples.append(GoldenSample(
            id="complex_001",
            input_prompt="Elabore uma defesa para licitação com valor de R$ 100.000, consultando jurisprudência do TCU sobre dispensa de licitação e validando a fundamentação legal",
            expected_output="Para elaborar a defesa adequada, é necessário considerar a jurisprudência do TCU sobre dispensa de licitação para valores até R$ 100.000...",
            category="elaboracao",
            difficulty="hard",
            legal_area="administrativo",
            expected_tools=["buscar_jurisprudencia_recente", "calcular_valor_causa", "validar_fundamentacao_legal", "buscar_legislacao_atualizada"],
            metadata={"valor": 100000, "tribunal": "TCU", "tema": "licitacao"}
        ))
    
    def get_sample(self, sample_id: str) -> Optional[GoldenSample]:
        """Busca uma amostra específica"""
        for sample in self.samples:
            if sample.id == sample_id:
                return sample
        return None
    
    def get_samples_by_category(self, category: str) -> List[GoldenSample]:
        """Busca amostras por categoria"""
        return [s for s in self.samples if s.category == category]
    
    def get_samples_by_difficulty(self, difficulty: str) -> List[GoldenSample]:
        """Busca amostras por dificuldade"""
        return [s for s in self.samples if s.difficulty == difficulty]
    
    def add_sample(self, sample: GoldenSample):
        """Adiciona uma nova amostra"""
        self.samples.append(sample)
    
    def export_to_json(self, filepath: str):
        """Exporta o dataset para JSON"""
        data = []
        for sample in self.samples:
            data.append({
                "id": sample.id,
                "input_prompt": sample.input_prompt,
                "expected_output": sample.expected_output,
                "category": sample.category,
                "difficulty": sample.difficulty,
                "legal_area": sample.legal_area,
                "expected_tools": sample.expected_tools,
                "metadata": sample.metadata
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

class QualityEvaluator:
    """Avaliador de qualidade dos agentes"""
    
    def __init__(self, golden_dataset: GoldenDataset):
        self.golden_dataset = golden_dataset
        self.evaluation_history: List[EvaluationResult] = []
    
    def _calculate_accuracy(self, expected: str, actual: str) -> float:
        """Calcula accuracy baseada em similaridade textual"""
        # Implementação simples - na produção usaria embeddings ou NLP
        expected_words = set(expected.lower().split())
        actual_words = set(actual.lower().split())
        
        if not expected_words:
            return 0.0
        
        intersection = expected_words.intersection(actual_words)
        union = expected_words.union(actual_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_completeness(self, expected_tools: List[str], tools_used: List[str]) -> float:
        """Calcula completeness baseada nas ferramentas utilizadas"""
        if not expected_tools:
            return 1.0
        
        expected_set = set(expected_tools)
        used_set = set(tools_used)
        
        return len(expected_set.intersection(used_set)) / len(expected_set)
    
    def _calculate_legal_compliance(self, output: str, legal_area: str) -> float:
        """Calcula compliance legal baseada em palavras-chave"""
        # Implementação simples - na produção usaria modelo específico
        legal_keywords = {
            "civil": ["código civil", "contrato", "obrigação", "responsabilidade"],
            "penal": ["código penal", "crime", "pena", "culpabilidade"],
            "administrativo": ["lei 8.666", "administração pública", "licitação", "contrato administrativo"],
            "geral": ["lei", "jurisprudência", "tribunal", "direito"]
        }
        
        keywords = legal_keywords.get(legal_area, legal_keywords["geral"])
        output_lower = output.lower()
        
        found_keywords = sum(1 for kw in keywords if kw in output_lower)
        return found_keywords / len(keywords) if keywords else 0.0
    
    def _calculate_coherence(self, output: str) -> float:
        """Calcula coerência do texto"""
        # Implementação simples - na produção usaria modelo de coerência
        sentences = output.split('.')
        
        if len(sentences) < 2:
            return 0.5
        
        # Verifica se há conectivos e estrutura lógica
        coherence_indicators = ["portanto", "assim", "dessa forma", "conforme", "segundo", "com base"]
        found_indicators = sum(1 for indicator in coherence_indicators if indicator in output.lower())
        
        return min(found_indicators / 3, 1.0)  # Normaliza para máximo 1.0
    
    def _calculate_citation_quality(self, output: str) -> float:
        """Calcula qualidade das citações"""
        # Implementação simples - na produção analisaria citações específicas
        citation_patterns = ["art.", "lei", "súmula", "acórdão", "tribunal", "julgado"]
        output_lower = output.lower()
        
        found_citations = sum(1 for pattern in citation_patterns if pattern in output_lower)
        return min(found_citations / 4, 1.0)  # Normaliza para máximo 1.0
    
    async def evaluate_sample(self, sample: GoldenSample, agent_function, tools_used: List[str]) -> EvaluationResult:
        """Avalia uma amostra específica"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Executa o agente
            agent_output = await agent_function(sample.input_prompt)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Calcula métricas
            metrics = {
                MetricType.ACCURACY: self._calculate_accuracy(sample.expected_output, agent_output),
                MetricType.COMPLETENESS: self._calculate_completeness(sample.expected_tools, tools_used),
                MetricType.LEGAL_COMPLIANCE: self._calculate_legal_compliance(agent_output, sample.legal_area),
                MetricType.RESPONSE_TIME: min(10.0 / execution_time, 1.0),  # Normaliza tempo (melhor = mais rápido)
                MetricType.COHERENCE: self._calculate_coherence(agent_output),
                MetricType.CITATION_QUALITY: self._calculate_citation_quality(agent_output)
            }
            
            result = EvaluationResult(
                sample_id=sample.id,
                agent_output=agent_output,
                metrics=metrics,
                execution_time=execution_time,
                tools_used=tools_used,
                timestamp=datetime.now()
            )
            
            self.evaluation_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Erro na avaliação da amostra {sample.id}: {e}")
            
            result = EvaluationResult(
                sample_id=sample.id,
                agent_output="",
                metrics={metric: 0.0 for metric in MetricType},
                execution_time=asyncio.get_event_loop().time() - start_time,
                tools_used=tools_used,
                timestamp=datetime.now(),
                error=str(e)
            )
            
            self.evaluation_history.append(result)
            return result
    
    async def evaluate_agent(self, agent_function, sample_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Avalia um agente em múltiplas amostras"""
        
        if sample_ids:
            samples = [self.golden_dataset.get_sample(sid) for sid in sample_ids]
            samples = [s for s in samples if s is not None]
        else:
            samples = self.golden_dataset.samples
        
        results = []
        
        for sample in samples:
            logger.info(f"Avaliando amostra {sample.id}")
            
            # Simula ferramentas utilizadas (na produção seria capturado do agente)
            tools_used = sample.expected_tools[:2]  # Simula uso parcial
            
            result = await self.evaluate_sample(sample, agent_function, tools_used)
            results.append(result)
        
        # Calcula estatísticas agregadas
        return self._calculate_aggregate_metrics(results)
    
    def _calculate_aggregate_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Calcula métricas agregadas"""
        
        if not results:
            return {}
        
        # Métricas por tipo
        metric_totals = {metric: 0.0 for metric in MetricType}
        
        for result in results:
            for metric, value in result.metrics.items():
                metric_totals[metric] += value
        
        # Calcula médias
        num_results = len(results)
        avg_metrics = {metric.value: total / num_results for metric, total in metric_totals.items()}
        
        # Estatísticas gerais
        successful_runs = len([r for r in results if r.error is None])
        avg_execution_time = sum(r.execution_time for r in results) / num_results
        
        # Score geral (média ponderada)
        weights = {
            MetricType.ACCURACY: 0.25,
            MetricType.COMPLETENESS: 0.20,
            MetricType.LEGAL_COMPLIANCE: 0.20,
            MetricType.COHERENCE: 0.15,
            MetricType.CITATION_QUALITY: 0.15,
            MetricType.RESPONSE_TIME: 0.05
        }
        
        overall_score = sum(
            metric_totals[metric] * weight for metric, weight in weights.items()
        ) / num_results
        
        return {
            "overall_score": overall_score,
            "metrics": avg_metrics,
            "total_samples": num_results,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / num_results,
            "avg_execution_time": avg_execution_time,
            "results": results
        }
    
    def generate_report(self, evaluation_results: Dict[str, Any]) -> str:
        """Gera relatório de avaliação"""
        
        report = f"""
=== RELATÓRIO DE AVALIAÇÃO DE QUALIDADE ===

📊 MÉTRICAS GERAIS:
• Score Geral: {evaluation_results['overall_score']:.2%}
• Taxa de Sucesso: {evaluation_results['success_rate']:.2%}
• Tempo Médio: {evaluation_results['avg_execution_time']:.2f}s
• Amostras Avaliadas: {evaluation_results['total_samples']}

📈 MÉTRICAS DETALHADAS:
"""
        
        for metric, value in evaluation_results['metrics'].items():
            report += f"• {metric.title().replace('_', ' ')}: {value:.2%}\n"
        
        report += f"\n🔍 ANÁLISE POR AMOSTRA:\n"
        
        for result in evaluation_results['results']:
            status = "✅ SUCESSO" if result.error is None else "❌ ERRO"
            report += f"• {result.sample_id}: {status} ({result.execution_time:.2f}s)\n"
        
        return report

# Exemplo de uso
async def exemplo_avaliacao():
    """Demonstra como usar o sistema de avaliação"""
    
    # Cria dataset e avaliador
    dataset = GoldenDataset()
    evaluator = QualityEvaluator(dataset)
    
    # Função de agente simulada
    async def agent_simulado(prompt: str) -> str:
        await asyncio.sleep(0.5)  # Simula processamento
        return f"Resposta simulada para: {prompt[:50]}..."
    
    # Avalia o agente
    results = await evaluator.evaluate_agent(agent_simulado)
    
    # Gera relatório
    report = evaluator.generate_report(results)
    print(report)

if __name__ == "__main__":
    asyncio.run(exemplo_avaliacao())
