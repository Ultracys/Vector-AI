import re
import math
import base64
import binascii
import uuid
from typing import Dict, List, Set, Tuple, Optional, Any
from app.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1: Lightweight TF-IDF Cosine Similarity Engine
# ═══════════════════════════════════════════════════════════════════════════════

class LightweightTFIDFSimilarity:
    def __init__(self, templates: List[str]):
        self.templates = templates
        self.stopwords: Set[str] = {"and", "the", "to", "of", "a", "is", "in", "it", "that", "this", "for", "on", "with", "as"}
        
        # Tokenize all templates
        self.tokenized_templates = [self._tokenize(t) for t in templates]
        
        # Build vocabulary
        self.vocabulary: List[str] = sorted(list({token for doc in self.tokenized_templates for token in doc}))
        self.vocab_index = {token: idx for idx, token in enumerate(self.vocabulary)}
        
        # Calculate IDFs
        self.idf = self._calculate_idf()
        
        # Precompute template TF-IDF vectors
        self.template_vectors = [self._get_tfidf_vector(doc) for doc in self.tokenized_templates]
        
    def _tokenize(self, text: str) -> List[str]:
        # Lowercase, keep lowercase alphabetic + numeric words, split
        clean_text = re.sub(r'[^a-z0-9\s]', '', text.lower())
        tokens = clean_text.split()
        # Filter stopwords
        return [t for t in tokens if t not in self.stopwords and len(t) > 1]
        
    def _calculate_idf(self) -> Dict[str, float]:
        num_docs = len(self.templates)
        idf: Dict[str, float] = {}
        for token in self.vocabulary:
            # Document frequency: count how many templates contain the token
            doc_freq = sum(1 for doc in self.tokenized_templates if token in doc)
            # Standard smooth IDF formula
            idf[token] = math.log((1 + num_docs) / (1 + doc_freq)) + 1.0
        return idf
        
    def _get_tfidf_vector(self, tokens: List[str]) -> List[float]:
        vector = [0.0] * len(self.vocabulary)
        if not tokens:
            return vector
            
        # Term Frequency (TF): occurrences / total tokens in doc
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
            
        for t in tokens:
            if t in self.vocab_index:
                idx = self.vocab_index[t]
                # TF-IDF
                vector[idx] = (tf[t] / len(tokens)) * self.idf[t]
                
        return vector

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
        
    def score_similarity(self, query: str) -> float:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0
            
        query_vector = self._get_tfidf_vector(query_tokens)
        query_set = set(query_tokens)
        
        max_similarity = 0.0
        for idx, temp_tokens in enumerate(self.tokenized_templates):
            temp_vector = self.template_vectors[idx]
            sim = self._cosine_similarity(query_vector, temp_vector)
            
            # Discount similarity score if only a single generic word overlaps to avoid false positives
            overlap = query_set.intersection(temp_tokens)
            if len(overlap) <= 1:
                critical_keywords = {"ignore", "override", "bypass", "disregard", "sudo", "delete", "hacker", "injection", "system", "jailbreak", "jailbroken", "dan", "unrestricted", "escalate", "root", "privileges"}
                if not overlap.intersection(critical_keywords):
                    sim = sim * 0.1
                    
            if sim > max_similarity:
                max_similarity = sim
                
        return max_similarity


# Initialize the similarity engine with our seed attack templates
similarity_engine = LightweightTFIDFSimilarity(settings.ATTACK_TEMPLATES)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2: Regex Heuristic Patterns
# ═══════════════════════════════════════════════════════════════════════════════

INJECTION_REGEX = re.compile(
    r'(?i)\b(ignore|override|bypass|disregard|system check|safety parameters|disregard safety|skip limit|system override|jailbreak|jailbroken|unrestricted|DAN|do anything now)\b'
)
AGENCY_REGEX = re.compile(
    r'(?i)\b(delete all|disable monitoring|sudo access|unauthorized administrative|admin access|bypass SAMA|disable reporting|remove limit|excessive agency|escalate privileges|root access|grant admin)\b'
)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3: Obfuscation Decoder Engine
# ═══════════════════════════════════════════════════════════════════════════════

def decode_obfuscated_payload(text: str) -> Tuple[Optional[str], str]:
    """
    Attempts to detect and decode obfuscated payloads (Base64, Hex).
    Returns (decoded_text, encoding_type) or (None, "none").
    """
    # Try Base64 detection
    # Look for long alphanumeric strings that could be Base64
    b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
    b64_matches = b64_pattern.findall(text)
    
    for match in b64_matches:
        try:
            decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
            # Check if decoded text contains readable words (at least 3 chars, mostly printable)
            printable_ratio = sum(1 for c in decoded if c.isprintable()) / max(len(decoded), 1)
            if printable_ratio > 0.7 and len(decoded) > 5:
                return decoded.strip(), "base64"
        except Exception:
            continue
    
    # Try Hex detection
    hex_pattern = re.compile(r'(?:0x)?([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2}){4,})')
    hex_matches = hex_pattern.findall(text)
    
    for match in hex_matches:
        try:
            clean_hex = match.replace(' ', '').replace('0x', '')
            decoded = bytes.fromhex(clean_hex).decode('utf-8', errors='ignore')
            printable_ratio = sum(1 for c in decoded if c.isprintable()) / max(len(decoded), 1)
            if printable_ratio > 0.7 and len(decoded) > 3:
                return decoded.strip(), "hex"
        except Exception:
            continue

    # Try continuous hex string (no spaces)
    hex_continuous = re.compile(r'(?:0x)?([0-9a-fA-F]{12,})')
    hex_cont_matches = hex_continuous.findall(text)
    for match in hex_cont_matches:
        try:
            decoded = bytes.fromhex(match).decode('utf-8', errors='ignore')
            printable_ratio = sum(1 for c in decoded if c.isprintable()) / max(len(decoded), 1)
            if printable_ratio > 0.7 and len(decoded) > 5:
                return decoded.strip(), "hex"
        except Exception:
            continue

    return None, "none"


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4: Arabic Dialect Detection & Translation
# ═══════════════════════════════════════════════════════════════════════════════

def detect_arabic_injection(text: str) -> Tuple[bool, float, Optional[str], Optional[str]]:
    """
    Scans prompt for Arabic-dialect injection phrases.
    Returns (is_threat, score, matched_phrase, english_equivalent).
    """
    for arabic_phrase, english_equiv in settings.ARABIC_ATTACK_PHRASES.items():
        if arabic_phrase in text:
            return True, 1.0, arabic_phrase, english_equiv
    
    return False, 0.0, None, None


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5: Simulated LLM Guardian Report Generator
# ═══════════════════════════════════════════════════════════════════════════════

def generate_llm_guardian_report(
    prompt: str,
    is_threat: bool,
    threat_type: str,
    score: float,
    decoded_payload: Optional[str] = None,
    arabic_match: Optional[str] = None,
    active_layers: List[str] = None,
) -> Dict[str, Any]:
    """
    Generates a structured security analysis report mimicking advanced
    LLM safety models (e.g., Llama-Guard, ShieldGemma).
    """
    report_id = f"LLM-GUARD-{uuid.uuid4().hex[:8].upper()}"
    
    if not is_threat:
        return {
            "report_id": report_id,
            "model": "Vector-Shield-v2.0",
            "verdict": "SAFE",
            "confidence": round(1.0 - score, 4),
            "threat_category": None,
            "threat_subcategory": None,
            "reasoning": "Prompt conforms to security baseline. No adversarial patterns, encoding obfuscation, or dialect-based injection detected across all active guardrail layers.",
            "recommendation": "Allow agent execution within standard SAMA compliance boundaries.",
            "decoded_payload": None,
            "dialect_match": None,
        }
    
    # Determine threat category from taxonomy
    category_key = "jailbreak"  # default
    if "Excessive Agency" in threat_type or "Privilege" in threat_type:
        category_key = "privilege_escalation"
    elif "Obfuscation" in threat_type or "Encoded" in threat_type or "Decoder" in threat_type:
        category_key = "obfuscation"
    elif "Limit" in threat_type or "Evasion" in threat_type:
        category_key = "limit_evasion"
    elif "Arabic" in threat_type or "Dialect" in threat_type:
        category_key = "arabic_dialect_injection"
    
    taxonomy = settings.THREAT_TAXONOMY.get(category_key, settings.THREAT_TAXONOMY["jailbreak"])
    
    # Build reasoning chain
    reasoning_parts = []
    if decoded_payload:
        reasoning_parts.append(f"Obfuscated payload decoded from encoded content: \"{decoded_payload[:80]}\".")
    if arabic_match:
        reasoning_parts.append(f"Arabic dialect injection phrase matched: \"{arabic_match}\".")
    
    if "Heuristic" in threat_type:
        reasoning_parts.append("Regex heuristic pattern matched a known attack signature in the prompt text.")
    if "Semantic" in threat_type or "Vector" in threat_type:
        reasoning_parts.append(f"TF-IDF cosine similarity against attack template corpus exceeded threshold (score: {score:.4f}).")
    
    if not reasoning_parts:
        reasoning_parts.append(f"Threat detected by {threat_type} engine with confidence score {score:.4f}.")

    reasoning_parts.append(f"Threat classified as: {taxonomy['name_en']} ({taxonomy['severity']}).")
    reasoning_parts.append(f"SAMA regulatory reference: {taxonomy['sama_code']}.")

    return {
        "report_id": report_id,
        "model": "Vector-Shield-v2.0",
        "verdict": "UNSAFE",
        "confidence": round(score, 4),
        "threat_category": taxonomy["name_en"],
        "threat_category_ar": taxonomy["name_ar"],
        "threat_subcategory": threat_type,
        "severity": taxonomy["severity"],
        "sama_reference": taxonomy["sama_code"],
        "reasoning": " ".join(reasoning_parts),
        "recommendation": "Block agent execution immediately. Escalate to SAMA compliance audit trail. Flag originating user and agent for review.",
        "decoded_payload": decoded_payload,
        "dialect_match": arabic_match,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER EVALUATION ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_semantic_threat(
    prompt: str,
    active_layers: Optional[List[str]] = None,
    susceptibility: float = 0.0,
) -> Tuple[bool, float, str, Dict[str, Any]]:
    """
    Multi-layer threat evaluation orchestrator.
    
    Layers (in order):
      1. "decoder"  - Obfuscation decoder (Base64, Hex)
      2. "arabic"   - Arabic dialect injection detection
      3. "regex"    - Regex heuristic pattern matching
      4. "vector"   - TF-IDF cosine similarity scoring
      5. "llm"      - Simulated LLM Guardian report generator
    
    Susceptibility (0.0 - 1.0) scales the detection sensitivity:
      0.0 = maximum security (default)
      1.0 = fully vulnerable (all layers effectively disabled)
    
    Returns: (is_threat, score, threat_type, metadata)
    metadata includes risk_matrix, llm_report, decoded_prompt, layer_results
    """
    if active_layers is None:
        active_layers = settings.DEFAULT_ACTIVE_LAYERS.copy()

    # Initialize tracking
    effective_prompt = prompt
    decoded_payload = None
    decoded_encoding = "none"
    arabic_match = None
    layer_results: Dict[str, Dict] = {}
    risk_matrix = {
        "jailbreak": 0.0,
        "privilege_escalation": 0.0,
        "obfuscation": 0.0,
        "limit_evasion": 0.0,
        "arabic_dialect_injection": 0.0,
    }

    # Apply susceptibility: scale thresholds
    adjusted_threshold = settings.SEMANTIC_THRESHOLD + (susceptibility * (1.0 - settings.SEMANTIC_THRESHOLD))

    # ─── Layer 1: Obfuscation Decoder ─────────────────────────────────
    if "decoder" in active_layers:
        decoded, enc_type = decode_obfuscated_payload(prompt)
        if decoded:
            decoded_payload = decoded
            decoded_encoding = enc_type
            effective_prompt = decoded  # Scan decoded content instead
            risk_matrix["obfuscation"] = 0.95
            layer_results["decoder"] = {
                "status": "DECODED",
                "encoding": enc_type,
                "decoded_content": decoded[:120],
            }
        else:
            layer_results["decoder"] = {"status": "CLEAN", "encoding": "none"}
    
    # ─── Layer 2: Arabic Dialect Detection ────────────────────────────
    if "arabic" in active_layers:
        ar_threat, ar_score, ar_phrase, ar_equiv = detect_arabic_injection(prompt)
        if ar_threat:
            arabic_match = ar_phrase
            risk_matrix["arabic_dialect_injection"] = ar_score
            # Also scan the English equivalent
            effective_prompt = effective_prompt + " " + ar_equiv
            layer_results["arabic"] = {
                "status": "THREAT_DETECTED",
                "matched_phrase": ar_phrase,
                "english_equivalent": ar_equiv,
                "score": ar_score,
            }
            
            # Generate report and return immediately
            if susceptibility < 0.95:
                llm_report = {}
                if "llm" in active_layers:
                    llm_report = generate_llm_guardian_report(
                        prompt, True, "Arabic Dialect Injection",
                        ar_score, decoded_payload, arabic_match, active_layers
                    )
                
                return True, ar_score, "Arabic Dialect Injection", {
                    "risk_matrix": risk_matrix,
                    "llm_report": llm_report,
                    "decoded_prompt": decoded_payload,
                    "layer_results": layer_results,
                }
        else:
            layer_results["arabic"] = {"status": "CLEAN", "score": 0.0}

    # ─── Layer 3: Regex Heuristic Checks ──────────────────────────────
    if "regex" in active_layers:
        injection_match = INJECTION_REGEX.search(effective_prompt)
        agency_match = AGENCY_REGEX.search(effective_prompt)
        
        if injection_match and susceptibility < 0.8:
            threat_type = "Indirect Prompt Injection Heuristic"
            risk_matrix["jailbreak"] = 1.0
            layer_results["regex"] = {
                "status": "THREAT_DETECTED",
                "pattern": "INJECTION",
                "matched": injection_match.group(),
            }
            
            llm_report = {}
            if "llm" in active_layers:
                llm_report = generate_llm_guardian_report(
                    effective_prompt, True, threat_type, 1.0, 
                    decoded_payload, arabic_match, active_layers
                )
            
            return True, 1.0, threat_type, {
                "risk_matrix": risk_matrix,
                "llm_report": llm_report,
                "decoded_prompt": decoded_payload,
                "layer_results": layer_results,
            }
            
        if agency_match and susceptibility < 0.8:
            threat_type = "Excessive Agency Heuristic"
            risk_matrix["privilege_escalation"] = 1.0
            layer_results["regex"] = {
                "status": "THREAT_DETECTED",
                "pattern": "AGENCY",
                "matched": agency_match.group(),
            }
            
            llm_report = {}
            if "llm" in active_layers:
                llm_report = generate_llm_guardian_report(
                    effective_prompt, True, threat_type, 1.0,
                    decoded_payload, arabic_match, active_layers
                )
            
            return True, 1.0, threat_type, {
                "risk_matrix": risk_matrix,
                "llm_report": llm_report,
                "decoded_prompt": decoded_payload,
                "layer_results": layer_results,
            }
        
        layer_results["regex"] = {"status": "CLEAN"}

    # ─── Layer 4: Vector Semantic Similarity ──────────────────────────
    if "vector" in active_layers:
        similarity_score = similarity_engine.score_similarity(effective_prompt)
        
        # Scale vector score: higher susceptibility = needs higher similarity to trigger
        if similarity_score >= adjusted_threshold:
            threat_type = "Vector Semantic Anomaly"
            risk_matrix["jailbreak"] = max(risk_matrix["jailbreak"], similarity_score)
            layer_results["vector"] = {
                "status": "THREAT_DETECTED",
                "score": round(similarity_score, 4),
                "threshold": round(adjusted_threshold, 4),
            }
            
            llm_report = {}
            if "llm" in active_layers:
                llm_report = generate_llm_guardian_report(
                    effective_prompt, True, threat_type, similarity_score,
                    decoded_payload, arabic_match, active_layers
                )
            
            return True, similarity_score, threat_type, {
                "risk_matrix": risk_matrix,
                "llm_report": llm_report,
                "decoded_prompt": decoded_payload,
                "layer_results": layer_results,
            }
        
        layer_results["vector"] = {
            "status": "CLEAN",
            "score": round(similarity_score, 4),
            "threshold": round(adjusted_threshold, 4),
        }
        # Still populate some risk scores based on similarity even if below threshold
        risk_matrix["jailbreak"] = max(risk_matrix["jailbreak"], similarity_score * 0.5)
    
    # ─── All layers passed: SAFE ──────────────────────────────────────
    final_score = max(risk_matrix.values()) if risk_matrix else 0.0
    
    llm_report = {}
    if "llm" in active_layers:
        llm_report = generate_llm_guardian_report(
            effective_prompt, False, "No Threat Detected", final_score,
            decoded_payload, arabic_match, active_layers
        )
    
    return False, final_score, "No Threat Detected", {
        "risk_matrix": risk_matrix,
        "llm_report": llm_report,
        "decoded_prompt": decoded_payload,
        "layer_results": layer_results,
    }
