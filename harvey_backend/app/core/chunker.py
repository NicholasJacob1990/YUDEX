"""
Chunker - Divisão inteligente de documentos jurídicos
Sistema especializado para segmentação de textos legais brasileiros
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..config import settings

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Tipos de chunks identificados"""
    ARTIGO = "artigo"
    PARAGRAFO = "paragrafo"
    INCISO = "inciso"
    ALINEA = "alinea"
    CAPITULO = "capitulo"
    SECAO = "secao"
    TITULO = "titulo"
    EMENTA = "ementa"
    FUNDAMENTACAO = "fundamentacao"
    DISPOSITIVO = "dispositivo"
    GENERIC = "generic"


@dataclass
class DocumentChunk:
    """Representa um chunk de documento jurídico"""
    chunk_id: str
    content: str
    chunk_type: ChunkType
    chunk_index: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any]
    parent_chunk_id: Optional[str] = None
    child_chunks: List[str] = None
    
    def __post_init__(self):
        if self.child_chunks is None:
            self.child_chunks = []


class LegalDocumentChunker:
    """
    Chunker especializado para documentos jurídicos brasileiros
    Reconhece estruturas legais como artigos, parágrafos, incisos, etc.
    """
    
    def __init__(
        self, 
        chunk_size: int = None, 
        chunk_overlap: int = None,
        preserve_structure: bool = True
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.preserve_structure = preserve_structure
        
        # Padrões regex para estruturas jurídicas
        self.patterns = {
            'artigo': r'(?:^|\n)\s*(?:Art\.?|Artigo)\s*(\d+)[\.\-º°ª]?\s*(.*?)(?=(?:\n\s*(?:Art\.?|Artigo)\s*\d+|$))',
            'paragrafo': r'(?:^|\n)\s*§\s*(\d+)[\.\-º°ª]?\s*(.*?)(?=(?:\n\s*§\s*\d+|\n\s*(?:Art\.?|Artigo)|\n\s*[IVX]+\s*[-\.]|$))',
            'inciso': r'(?:^|\n)\s*([IVX]+)\s*[-\.\)]\s*(.*?)(?=(?:\n\s*[IVX]+\s*[-\.\)]|\n\s*[a-z]\)\s*|\n\s*§|\n\s*(?:Art\.?|Artigo)|$))',
            'alinea': r'(?:^|\n)\s*([a-z])\)\s*(.*?)(?=(?:\n\s*[a-z]\)\s*|\n\s*[IVX]+\s*[-\.\)]|\n\s*§|\n\s*(?:Art\.?|Artigo)|$))',
            'capitulo': r'(?:^|\n)\s*(?:CAPÍTULO|Capítulo)\s*([IVX]+|[0-9]+)\s*(.*?)(?=(?:\n\s*(?:CAPÍTULO|Capítulo)|\n\s*(?:SEÇÃO|Seção)|\n\s*(?:Art\.?|Artigo)|$))',
            'secao': r'(?:^|\n)\s*(?:SEÇÃO|Seção)\s*([IVX]+|[0-9]+)\s*(.*?)(?=(?:\n\s*(?:SEÇÃO|Seção)|\n\s*(?:CAPÍTULO|Capítulo)|\n\s*(?:Art\.?|Artigo)|$))',
            'titulo': r'(?:^|\n)\s*(?:TÍTULO|Título)\s*([IVX]+|[0-9]+)\s*(.*?)(?=(?:\n\s*(?:TÍTULO|Título)|\n\s*(?:CAPÍTULO|Capítulo)|$))'
        }
        
        # Padrões para identificar tipos especiais de documento
        self.document_patterns = {
            'lei': r'Lei\s+n[ºª°]?\s*[\d\.,/]+',
            'decreto': r'Decreto\s+n[ºª°]?\s*[\d\.,/]+',
            'resolucao': r'Resolução\s+n[ºª°]?\s*[\d\.,/]+',
            'acordao': r'Acórdão\s+n[ºª°]?\s*[\d\.,/]+',
            'jurisprudencia': r'(?:STF|STJ|TST|TCU|TRF|TJSP|TJRJ)',
            'parecer': r'PARECER\s+(?:JURÍDICO|TÉCNICO)',
            'peticao': r'(?:PETIÇÃO|INICIAL|CONTESTAÇÃO|TRÉPLICA)'
        }
    
    def chunk_document(
        self, 
        text: str, 
        document_type: str = "generic",
        metadata: Dict[str, Any] = None
    ) -> List[DocumentChunk]:
        """
        Divide documento em chunks inteligentes
        """
        if not text.strip():
            return []
        
        metadata = metadata or {}
        
        # Detecta tipo de documento se não especificado
        if document_type == "generic":
            document_type = self._detect_document_type(text)
        
        # Escolhe estratégia de chunking baseada no tipo
        if self.preserve_structure and document_type in ['lei', 'decreto', 'resolucao']:
            return self._chunk_structured_legal_document(text, document_type, metadata)
        elif document_type == 'jurisprudencia':
            return self._chunk_jurisprudence_document(text, metadata)
        elif document_type == 'parecer':
            return self._chunk_opinion_document(text, metadata)
        else:
            return self._chunk_generic_document(text, document_type, metadata)
    
    def _detect_document_type(self, text: str) -> str:
        """Detecta o tipo de documento baseado em padrões"""
        text_sample = text[:2000].upper()  # Analisa apenas o início
        
        for doc_type, pattern in self.document_patterns.items():
            if re.search(pattern, text_sample, re.IGNORECASE):
                logger.info(f"Documento detectado como: {doc_type}")
                return doc_type
        
        return "generic"
    
    def _chunk_structured_legal_document(
        self, 
        text: str, 
        document_type: str, 
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Chunking para documentos legais estruturados (leis, decretos)
        """
        chunks = []
        chunk_counter = 0
        
        # Primeiro, identifica estruturas principais
        sections = self._extract_hierarchical_structure(text)
        
        for section in sections:
            # Cria chunk para cada seção estrutural
            chunk = DocumentChunk(
                chunk_id=f"chunk_{chunk_counter}",
                content=section['content'],
                chunk_type=ChunkType(section['type']),
                chunk_index=chunk_counter,
                start_position=section['start'],
                end_position=section['end'],
                metadata={
                    **metadata,
                    'section_number': section.get('number'),
                    'section_title': section.get('title'),
                    'hierarchy_level': section.get('level', 0),
                    'document_type': document_type
                }
            )
            
            # Se o chunk é muito grande, subdivide mantendo a estrutura
            if len(section['content']) > self.chunk_size:
                sub_chunks = self._subdivide_large_chunk(chunk)
                chunks.extend(sub_chunks)
                chunk_counter += len(sub_chunks)
            else:
                chunks.append(chunk)
                chunk_counter += 1
        
        return chunks
    
    def _extract_hierarchical_structure(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrai estrutura hierárquica do documento (títulos, capítulos, artigos)
        """
        sections = []
        
        # Primeiro passa: identifica todas as seções
        all_matches = []
        
        for structure_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
                all_matches.append({
                    'type': structure_type,
                    'start': match.start(),
                    'end': match.end(),
                    'number': match.group(1) if match.groups() else None,
                    'content': match.group(0),
                    'title': match.group(2) if len(match.groups()) > 1 else None
                })
        
        # Ordena por posição no texto
        all_matches.sort(key=lambda x: x['start'])
        
        # Segunda passa: determina hierarquia e conteúdo completo
        hierarchy_levels = {
            'titulo': 1,
            'capitulo': 2,
            'secao': 3,
            'artigo': 4,
            'paragrafo': 5,
            'inciso': 6,
            'alinea': 7
        }
        
        for i, match in enumerate(all_matches):
            # Determina onde essa seção termina
            end_pos = len(text)
            level = hierarchy_levels.get(match['type'], 8)
            
            # Encontra próxima seção do mesmo nível ou superior
            for j in range(i + 1, len(all_matches)):
                next_level = hierarchy_levels.get(all_matches[j]['type'], 8)
                if next_level <= level:
                    end_pos = all_matches[j]['start']
                    break
            
            # Extrai conteúdo completo da seção
            full_content = text[match['start']:end_pos].strip()
            
            sections.append({
                'type': match['type'],
                'start': match['start'],
                'end': end_pos,
                'number': match['number'],
                'title': match['title'],
                'content': full_content,
                'level': level
            })
        
        return sections
    
    def _chunk_generic_document(
        self, 
        text: str, 
        document_type: str, 
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Chunking genérico para documentos sem estrutura específica
        """
        chunks = []
        
        # Divide por sentenças preservando contexto
        text_chunks = self._split_by_sentences(text, self.chunk_size, self.chunk_overlap)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                chunk_id=f"chunk_{i}",
                content=chunk_text,
                chunk_type=ChunkType.GENERIC,
                chunk_index=i,
                start_position=0,  # Aproximado
                end_position=len(chunk_text),
                metadata={
                    **metadata,
                    'document_type': document_type,
                    'chunk_method': 'generic'
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_sentences(
        self, 
        text: str, 
        max_size: int, 
        overlap: int
    ) -> List[str]:
        """
        Divide texto por sentenças respeitando tamanho máximo
        """
        # Padrão para identificar fim de sentença em textos jurídicos
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=\.)\s*(?=\d+[\.\)])|(?<=art\.)\s+(?=\d+)'
        
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Se adicionar esta sentença ultrapassar o limite
            if len(current_chunk) + len(sentence) > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Calcula overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    # Pega as últimas palavras para overlap
                    words = current_chunk.split()
                    overlap_words = []
                    overlap_chars = 0
                    
                    for word in reversed(words):
                        if overlap_chars + len(word) + 1 <= overlap:
                            overlap_words.insert(0, word)
                            overlap_chars += len(word) + 1
                        else:
                            break
                    
                    current_chunk = " ".join(overlap_words) + " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Adiciona último chunk se houver
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _subdivide_large_chunk(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """
        Subdivide chunk muito grande mantendo contexto
        """
        sub_texts = self._split_by_sentences(
            chunk.content, 
            self.chunk_size, 
            self.chunk_overlap
        )
        
        sub_chunks = []
        
        for i, sub_text in enumerate(sub_texts):
            sub_chunk = DocumentChunk(
                chunk_id=f"{chunk.chunk_id}_sub_{i}",
                content=sub_text,
                chunk_type=chunk.chunk_type,
                chunk_index=chunk.chunk_index + i,
                start_position=chunk.start_position,
                end_position=chunk.end_position,
                metadata={
                    **chunk.metadata,
                    'is_subdivision': True,
                    'parent_chunk_id': chunk.chunk_id,
                    'sub_index': i,
                    'total_subs': len(sub_texts)
                },
                parent_chunk_id=chunk.chunk_id
            )
            sub_chunks.append(sub_chunk)
        
        return sub_chunks


# Função conveniente para chunking
def chunk_legal_document(
    text: str,
    document_type: str = "generic",
    chunk_size: int = None,
    chunk_overlap: int = None,
    metadata: Dict[str, Any] = None
) -> List[DocumentChunk]:
    """
    Função conveniente para fazer chunking de documento jurídico
    """
    chunker = LegalDocumentChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    return chunker.chunk_document(text, document_type, metadata)
