import spacy
from typing import List, Dict, Set, Optional
from collections import defaultdict
import re

from backend.config import settings
from backend.models.schemas import Paper, Entity


class EntityExtractor:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.SCISPACY_MODEL
        self.nlp = None
        self._stopwords = self._get_stopwords()

    def _get_stopwords(self) -> Set[str]:
        return {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "can", "this",
            "that", "these", "those", "it", "its", "we", "our", "you", "your",
            "they", "their", "he", "his", "she", "her", "which", "who", "whom",
            "what", "when", "where", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just", "also",
            "now", "here", "there", "then", "once", "if", "because", "while",
            "although", "though", "after", "before", "during", "between", "through",
            "about", "against", "into", "throughout", "despite", "however", "therefore",
            "thus", "hence", "furthermore", "moreover", "using", "used", "use",
            "approach", "method", "technique", "system", "model", "result", "results",
            "study", "studies", "paper", "work", "research", "analysis", "data",
            "based", "proposed", "presented", "shown", "demonstrated", "investigated",
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "first", "second", "third", "fourth", "fifth", "ieee", "acm",
            "fig", "figure", "table", "section", "chapter", "conclusion", "introduction",
            "abstract", "keywords", "references", "acknowledgments", "et", "al",
            "etc", "ie", "eg", "vs", "per", "etc", "upon", "towards", "within",
            "without", "under", "over", "above", "below", "across", "around",
            "behind", "beside", "beyond", "outside", "inside", "whether", "either",
            "neither", "until", "unless", "since", "so", "yet", "still", "already",
            "again", "further", "instead", "rather", "almost", "already", "even",
            "ever", "just", "likely", "mainly", "mostly", "nearly", "often",
            "quite", "rather", "really", "seldom", "significantly", "simply",
            "sometimes", "soon", "still", "then", "therefore", "thus", "too",
            "usually", "very", "well", "whereas", "yet", "many", "much", "more",
            "most", "less", "least", "better", "best", "worse", "worst", "later",
            "latest", "earlier", "earliest", "higher", "highest", "lower", "lowest",
            "newer", "newest", "older", "oldest", "greater", "greatest", "fewer",
            "fewest", "further", "furthest", "farther", "farthest", "following",
            "previous", "next", "last", "current", "present", "past", "future",
            "recent", "latest", "early", "late", "previous", "subsequent", "prior",
            "latter", "former", "various", "different", "similar", "same", "common",
            "specific", "general", "particular", "special", "certain", "several",
            "various", "numerous", "multiple", "few", "little", "some", "any",
            "many", "much", "more", "most", "less", "least", "enough", "sufficient",
            "necessary", "required", "needed", "essential", "important", "significant",
            "crucial", "critical", "key", "main", "primary", "secondary", "major",
            "minor", "central", "principal", "chief", "leading", "top", "high",
            "low", "big", "large", "small", "little", "long", "short", "wide",
            "narrow", "deep", "shallow", "thick", "thin", "heavy", "light", "fast",
            "quick", "slow", "rapid", "gradual", "sudden", "immediate", "instant",
            "direct", "indirect", "simple", "complex", "basic", "fundamental",
            "advanced", "modern", "traditional", "classical", "contemporary", "novel",
            "new", "old", "original", "existing", "current", "available", "possible",
            "potential", "future", "actual", "real", "true", "false", "correct",
            "incorrect", "right", "wrong", "valid", "invalid", "effective", "efficient",
            "successful", "unsuccessful", "useful", "useless", "helpful", "harmful",
            "beneficial", "detrimental", "positive", "negative", "good", "bad",
            "excellent", "poor", "great", "terrible", "wonderful", "awful", "nice",
            "fine", "okay", "ok", "satisfactory", "unsatisfactory", "appropriate",
            "inappropriate", "suitable", "unsuitable", "proper", "improper", "accurate",
            "inaccurate", "precise", "imprecise", "exact", "approximate", "rough",
            "detailed", "brief", "concise", "comprehensive", "complete", "incomplete",
            "full", "partial", "whole", "entire", "total", "overall", "general",
            "specific", "particular", "individual", "separate", "single", "unique",
            "common", "rare", "unusual", "normal", "abnormal", "standard", "typical",
            "atypical", "regular", "irregular", "constant", "variable", "continuous",
            "discrete", "periodic", "occasional", "frequent", "infrequent", "daily",
            "weekly", "monthly", "yearly", "annual", "monthly", "daily", "hourly",
            "minute", "second", "moment", "instant", "period", "phase", "stage",
            "step", "level", "degree", "extent", "amount", "quantity", "number",
            "value", "rate", "ratio", "percentage", "proportion", "part", "portion",
            "segment", "section", "region", "area", "zone", "domain", "field",
            "scope", "range", "scale", "size", "dimension", "aspect", "angle",
            "direction", "orientation", "position", "location", "place", "point",
            "line", "surface", "plane", "space", "volume", "area", "length", "width",
            "height", "depth", "distance", "path", "route", "way", "direction",
            "approach", "entry", "exit", "input", "output", "source", "target",
            "destination", "origin", "start", "end", "beginning", "middle", "center",
            "core", "heart", "focus", "attention", "emphasis", "priority", "preference",
            "choice", "selection", "decision", "option", "alternative", "solution",
            "answer", "response", "reply", "reaction", "behavior", "action", "activity",
            "process", "procedure", "operation", "function", "task", "job", "work",
            "effort", "attempt", "try", "test", "experiment", "trial", "evaluation",
            "assessment", "measurement", "calculation", "estimation", "prediction",
            "forecast", "projection", "expectation", "assumption", "hypothesis",
            "theory", "principle", "concept", "idea", "notion", "thought", "view",
            "perspective", "approach", "methodology", "strategy", "plan", "design",
            "architecture", "structure", "organization", "arrangement", "configuration",
            "pattern", "format", "layout", "scheme", "system", "mechanism", "device",
            "component", "element", "part", "unit", "module", "block", "segment",
            "piece", "item", "object", "entity", "thing", "matter", "stuff", "material",
            "substance", "content", "body", "mass", "weight", "force", "energy",
            "power", "strength", "intensity", "magnitude", "amplitude", "frequency",
            "speed", "velocity", "acceleration", "momentum", "inertia", "resistance",
            "pressure", "stress", "strain", "tension", "compression", "shear",
            "torque", "rotation", "motion", "movement", "shift", "change", "transition",
            "transformation", "conversion", "variation", "modification", "adjustment",
            "adaptation", "evolution", "development", "growth", "progress", "advance",
            "improvement", "enhancement", "optimization", "refinement", "simplification",
            "complexity", "simplicity", "difficulty", "ease", "challenge", "problem",
            "issue", "question", "concern", "topic", "subject", "theme", "matter",
            "case", "example", "instance", "sample", "specimen", "illustration",
            "demonstration", "indication", "evidence", "proof", "confirmation",
            "verification", "validation", "testing", "checking", "inspection",
            "examination", "review", "survey", "investigation", "analysis", "study",
            "research", "exploration", "discovery", "finding", "observation",
            "measurement", "detection", "identification", "recognition", "classification",
            "categorization", "grouping", "clustering", "sorting", "ordering",
            "arrangement", "organization", "management", "control", "monitoring",
            "tracking", "supervision", "coordination", "integration", "combination",
            "fusion", "merger", "union", "joining", "connection", "link", "relationship",
            "association", "correlation", "dependency", "independence", "similarity",
            "difference", "equality", "inequality", "comparison", "contrast", "match",
            "mismatch", "agreement", "disagreement", "consistency", "inconsistency",
            "compatibility", "incompatibility", "parallel", "series", "sequence",
            "chain", "cycle", "loop", "iteration", "repetition", "duplication",
            "replication", "copy", "clone", "original", "version", "variant",
            "derivative", "modification", "adaptation", "extension", "expansion",
            "contraction", "reduction", "decrease", "increase", "growth", "decline",
            "rise", "fall", "drop", "jump", "leap", "surge", "plunge", "peak",
            "valley", "minimum", "maximum", "optimum", "threshold", "limit", "boundary",
            "border", "edge", "margin", "interval", "range", "scope", "span", "period",
            "duration", "time", "timing", "schedule", "calendar", "clock", "watch",
            "timer", "stopwatch", "deadline", "due", "expiration", "timeout", "delay",
            "pause", "halt", "stop", "start", "begin", "resume", "continue", "proceed",
            "advance", "progress", "move", "travel", "go", "come", "leave", "arrive",
            "enter", "exit", "open", "close", "enable", "disable", "activate",
            "deactivate", "turn", "switch", "toggle", "set", "reset", "initialize",
            "configure", "setup", "prepare", "ready", "load", "unload", "save",
            "store", "retrieve", "fetch", "get", "put", "send", "receive", "transmit",
            "transfer", "move", "copy", "paste", "cut", "delete", "remove", "add",
            "insert", "append", "prepend", "replace", "update", "modify", "change",
            "alter", "transform", "convert", "translate", "encode", "decode", "encrypt",
            "decrypt", "compress", "decompress", "pack", "unpack", "merge", "split",
            "join", "separate", "divide", "multiply", "sum", "average", "mean",
            "median", "mode", "standard", "deviation", "variance", "covariance",
            "correlation", "regression", "interpolation", "extrapolation", "integration",
            "differentiation", "derivative", "integral", "limit", "boundary", "condition",
            "constraint", "requirement", "specification", "definition", "description",
            "explanation", "interpretation", "annotation", "comment", "note", "remark",
            "observation", "statement", "declaration", "assertion", "claim", "argument",
            "reason", "cause", "effect", "result", "consequence", "outcome", "impact",
            "influence", "contribution", "role", "function", "purpose", "goal", "objective",
            "target", "aim", "intention", "motivation", "incentive", "driver", "factor",
            "element", "component", "ingredient", "feature", "characteristic", "property",
            "attribute", "quality", "trait", "aspect", "dimension", "parameter", "variable",
            "constant", "coefficient", "exponent", "base", "power", "root", "square",
            "cube", "logarithm", "exponential", "trigonometric", "geometry", "algebra",
            "calculus", "statistics", "probability", "logic", "boolean", "binary",
            "decimal", "hexadecimal", "octal", "base64", "encoding", "format", "protocol",
            "standard", "specification", "interface", "API", "library", "framework",
            "platform", "environment", "system", "operating", "OS", "kernel", "driver",
            "firmware", "hardware", "software", "program", "application", "app", "tool",
            "utility", "module", "package", "component", "service", "server", "client",
            "browser", "database", "storage", "memory", "cache", "buffer", "register",
            "file", "folder", "directory", "path", "URL", "URI", "endpoint", "route",
            "resource", "asset", "object", "class", "instance", "object", "type", "kind",
            "sort", "category", "class", "genre", "style", "form", "shape", "structure",
            "pattern", "template", "model", "schema", "design", "layout", "blueprint",
            "architecture", "diagram", "chart", "graph", "plot", "table", "matrix",
            "array", "list", "set", "map", "dictionary", "hash", "queue", "stack",
            "tree", "graph", "network", "node", "edge", "vertex", "link", "connection",
            "path", "route", "circuit", "loop", "cycle", "chain", "sequence", "stream",
            "flow", "current", "signal", "data", "information", "knowledge", "wisdom",
            "intelligence", "learning", "training", "inference", "prediction", "classification",
            "regression", "clustering", "dimensionality", "reduction", "feature", "engineering",
            "preprocessing", "postprocessing", "optimization", "hyperparameter", "tuning",
            "validation", "testing", "evaluation", "metric", "score", "accuracy", "precision",
            "recall", "F1", "AUC", "ROC", "curve", "loss", "error", "gradient", "descent",
            "backpropagation", "forward", "feedforward", "recurrent", "convolutional",
            "transformer", "attention", "mechanism", "embedding", "token", "vocabulary",
            "corpus", "dataset", "collection", "repository", "archive", "database",
            "warehouse", "lake", "pipeline", "workflow", "process", "thread", "task",
            "job", "worker", "pool", "queue", "scheduler", "orchestrator", "manager",
            "controller", "handler", "listener", "observer", "subscriber", "publisher",
            "event", "message", "notification", "alert", "warning", "error", "exception",
            "failure", "success", "status", "state", "mode", "context", "environment",
            "scope", "namespace", "scope", "closure", "callback", "function", "method",
            "procedure", "routine", "subroutine", "algorithm", "heuristic", "rule", "policy",
            "strategy", "pattern", "antipattern", "best", "practice", "convention", "standard",
            "norm", "guideline", "recommendation", "suggestion", "advice", "tip", "trick",
            "hack", "workaround", "solution", "fix", "patch", "update", "upgrade", "downgrade",
            "version", "release", "build", "commit", "branch", "merge", "conflict", "resolve",
            "review", "audit", "inspection", "validation", "verification", "certification",
            "accreditation", "compliance", "regulation", "law", "policy", "agreement",
            "contract", "license", "terms", "conditions", "privacy", "security", "safety",
            "protection", "defense", "attack", "threat", "vulnerability", "risk", "mitigation",
            "prevention", "detection", "response", "recovery", "backup", "restore", "disaster",
            "recovery", "business", "continuity", "availability", "reliability", "scalability",
            "performance", "efficiency", "latency", "throughput", "bandwidth", "capacity",
            "utilization", "workload", "demand", "supply", "resource", "allocation", "scheduling",
            "prioritization", "queuing", "buffering", "caching", "prefetching", "loading",
            "unloading", "streaming", "processing", "computation", "calculation", "operation",
            "execution", "runtime", "compile", "time", "build", "time", "deployment", "time",
            "maintenance", "time", "downtime", "uptime", "availability", "MTBF", "MTTR",
            "SLA", "QoS", "KPI", "metric", "measurement", "monitoring", "observability",
            "telemetry", "logging", "tracing", "profiling", "debugging", "troubleshooting",
            "diagnosis", "root", "cause", "analysis", " RCA", "incident", "management", "problem",
            "management", "change", "management", "configuration", "management", "release",
            "management", "deployment", "CI/CD", "continuous", "integration", "continuous",
            "delivery", "continuous", "deployment", "automation", "orchestration", "container",
            "virtualization", "cloud", "native", "microservices", "service-oriented", "architecture",
            "SOA", "monolith", "distributed", "system", "cluster", "node", "instance", "pod",
            "container", "VM", "virtual", "machine", "serverless", "lambda", "function", "as",
            "a", "service", "IaaS", "PaaS", "SaaS", "FaaS", "CaaS", "edge", "computing",
            "fog", "computing", "grid", "computing", "parallel", "computing", "distributed",
            "computing", "quantum", "computing", "neural", "computing", "biological", "computing",
            "analog", "computing", "digital", "computing", "hybrid", "computing", "high",
            "performance", "HPC", "supercomputing", "grid", "cluster", "cloud", "edge",
            "fog", "mist", "dew", "peer-to-peer", "P2P", "blockchain", "distributed", "ledger",
            "smart", "contract", "cryptocurrency", "token", "coin", "wallet", "mining", "staking",
            "consensus", "mechanism", "PoW", "PoS", "DPoS", "PBFT", "Raft", "Paxos", "ZAB",
            "gossip", "protocol", "epidemic", "protocol", "failure", "detector", "heartbeat",
            "lease", "lock", "mutex", "semaphore", "condition", "variable", "monitor", "barrier",
            "countdown", "latch", "atomic", "operation", "transaction", "ACID", "BASE", "CAP",
            "theorem", "PACELC", "theorem", "eventual", "consistency", "strong", "consistency",
            "weak", "consistency", "causal", "consistency", "sequential", "consistency", "linearizability",
            "serializability", "isolation", "level", "read", "committed", "read", "uncommitted",
            "repeatable", "read", "serializable", "snapshot", "isolation", "MVCC", "multi-version",
            "concurrency", "control", "optimistic", "concurrency", "control", "OCC", "pessimistic",
            "concurrency", "control", "deadlock", "livelock", "starvation", "race", "condition",
            "data", "race", "heisenbug", "mandelbug", "schrodinbug", "bohrbug", "bug", "defect",
            "error", "fault", "failure", "crash", "hang", "freeze", "panic", "abort", "exit",
            "termination", "signal", "exception", "interrupt", "trap", "fault", "page", "fault",
            "segmentation", "fault", "SIGSEGV", "SIGILL", "SIGABRT", "SIGFPE", "SIGBUS", "SIGSYS",
            "core", "dump", "stack", "trace", "call", "stack", "stack", "frame", "instruction",
            "pointer", "program", "counter", "register", "accumulator", "stack", "pointer", "base",
            "pointer", "index", "register", "general", "purpose", "register", "special", "purpose",
            "register", "control", "register", "status", "register", "flag", "bit", "byte", "word",
            "double", "word", "quad", "word", "octa", "word", "nibble", "bit", "binary", "digit",
            "hexadecimal", "octal", "decimal", "binary", "base", "conversion", "two's", "complement",
            "one's", "complement", "sign-magnitude", "floating", "point", "fixed", "point", "integer",
            "natural", "number", "rational", "number", "real", "number", "complex", "number", "irrational",
            "number", "transcendental", "number", "prime", "number", "composite", "number", "even",
            "number", "odd", "number", "positive", "number", "negative", "number", "zero", "one",
            "infinity", "NaN", "not", "a", "number", "epsilon", "precision", "accuracy", "error",
            "tolerance", "approximation", "estimation", "rounding", "truncation", "floor", "ceiling",
            "absolute", "value", "magnitude", "sign", "direction", "angle", "degree", "radian", "gradient",
            "slope", "intercept", "asymptote", "tangent", "secant", "cosecant", "sine", "cosine",
            "tangent", "cotangent", "arcsine", "arccosine", "arctangent", "hyperbolic", "sine",
            "hyperbolic", "cosine", "hyperbolic", "tangent", "exponential", "logarithm", "natural",
            "logarithm", "common", "logarithm", "power", "root", "square", "root", "cube", "root",
            "factorial", "permutation", "combination", "binomial", "coefficient", "polynomial", "monomial",
            "binomial", "trinomial", "quadratic", "cubic", "quartic", "quintic", "linear", "exponential",
            "logarithmic", "trigonometric", "periodic", "aperiodic", "monotonic", "non-monotonic",
            "convex", "concave", "continuous", "discontinuous", "differentiable", "integrable", "analytic",
            "holomorphic", "meromorphic", "entire", "rational", "function", "irrational", "function",
            "algebraic", "function", "transcendental", "function", "composite", "function", "inverse",
            "function", "piecewise", "function", "recursive", "function", "lambda", "function", "closure",
            "currying", "partial", "application", "higher-order", "function", "pure", "function", "impure",
            "function", "side", "effect", "mutation", "immutability", "referential", "transparency",
            "determinism", "non-determinism", "idempotence", "commutative", "associative", "distributive",
            "identity", "element", "inverse", "element", "neutral", "element", "absorbing", "element",
            "semigroup", "monoid", "group", "abelian", "group", "ring", "field", "vector", "space",
            "linear", "algebra", "matrix", "vector", "scalar", "tensor", "determinant", "eigenvalue",
            "eigenvector", "singular", "value", "decomposition", "SVD", "principal", "component", "analysis",
            "PCA", "factor", "analysis", "cluster", "analysis", "discriminant", "analysis", "regression",
            "analysis", "time", "series", "analysis", "frequency", "analysis", "spectral", "analysis",
            "wavelet", "transform", "Fourier", "transform", "Laplace", "transform", "Z-transform",
            "convolution", "correlation", "autocorrelation", "cross-correlation", "covariance", "variance",
            "standard", "deviation", "mean", "median", "mode", "range", "interquartile", "range", "percentile",
            "quantile", "quartile", "outlier", "anomaly", "normal", "distribution", "Gaussian", "distribution",
            "Poisson", "distribution", "binomial", "distribution", "exponential", "distribution", "uniform",
            "distribution", "chi-square", "distribution", "t-distribution", "F-distribution", "beta", "distribution",
            "gamma", "distribution", "Weibull", "distribution", "log-normal", "distribution", "Pareto",
            "distribution", "Cauchy", "distribution", "Bernoulli", "distribution", "geometric", "distribution",
            "hypergeometric", "distribution", "negative", "binomial", "distribution", "multinomial", "distribution",
            "multivariate", "normal", "distribution", "Dirichlet", "distribution", "conjugate", "prior",
            "posterior", "distribution", "likelihood", "marginal", "likelihood", "conditional", "probability",
            "joint", "probability", "Bayes'", "theorem", "Bayesian", "inference", "maximum", "likelihood",
            "estimation", "MLE", "maximum", "a", "posteriori", "estimation", "MAP", "expectation-maximization",
            "algorithm", "EM", "algorithm", "Monte", "Carlo", "method", "Markov", "chain", "Monte", "Carlo",
            "MCMC", "Gibbs", "sampling", "Metropolis-Hastings", "algorithm", "rejection", "sampling", "importance",
            "sampling", "particle", "filter", "Kalman", "filter", "extended", "Kalman", "filter", "unscented",
            "Kalman", "filter", "hidden", "Markov", "model", "HMM", "conditional", "random", "field", "CRF",
            "graphical", "model", "Bayesian", "network", "belief", "network", "influence", "diagram", "decision",
            "network", "Markov", "random", "field", "MRF", "Ising", "model", "Potts", "model", "Boltzmann",
            "machine", "restricted", "Boltzmann", "machine", "RBM", "deep", "belief", "network", "DBN", "deep",
            "Boltzmann", "machine", "DBM", "autoencoder", "variational", "autoencoder", "VAE", "denoising",
            "autoencoder", "sparse", "autoencoder", "contractive", "autoencoder", "convolutional", "autoencoder",
            "generative", "adversarial", "network", "GAN", "conditional", "GAN", "InfoGAN", "Wasserstein", "GAN",
            "WGAN", "cycle-consistent", "GAN", "CycleGAN", "style", "transfer", "neural", "style", "transfer",
            "attention", "mechanism", "self-attention", "multi-head", "attention", "scaled", "dot-product", "attention",
            "additive", "attention", "location-based", "attention", "content-based", "attention", "hierarchical",
            "attention", "recurrent", "attention", "memory", "attention", "pointer", "network", "transformer",
            "encoder", "decoder", "encoder-decoder", "sequence-to-sequence", "seq2seq", "beam", "search", "greedy",
            "search", "nucleus", "sampling", "top-k", "sampling", "temperature", "scaling", "label", "smoothing",
            "dropout", "batch", "normalization", "layer", "normalization", "instance", "normalization", "group",
            "normalization", "weight", "normalization", "residual", "connection", "skip", "connection", "highway",
            "network", "dense", "connection", " densely", "connected", "convolutional", "network", "DenseNet",
            "residual", "network", "ResNet", "Inception", "network", "GoogLeNet", "VGG", "network", "AlexNet",
            "LeNet", "MobileNet", "EfficientNet", "Vision", "Transformer", "ViT", "Swin", "Transformer", "DeiT",
            "BEiT", "MAE", "Masked", "Autoencoder", "CLIP", "Contrastive", "Language-Image", "Pretraining", "DALL-E",
            "Stable", "Diffusion", "diffusion", "model", "denoising", "diffusion", "probabilistic", "model", "DDPM",
            "score-based", "generative", "model", "flow-based", "generative", "model", "normalizing", "flow",
            "autoregressive", "generative", "model", "language", "model", "LM", "large", "language", "model", "LLM",
            "GPT", "Generative", "Pretrained", "Transformer", "BERT", "Bidirectional", "Encoder", "Representations",
            "from", "Transformers", "RoBERTa", "ALBERT", "DistilBERT", "T5", "Text-to-Text", "Transfer", "Transformer",
            "BART", "GPT-2", "GPT-3", "GPT-3.5", "GPT-4", "LLaMA", "Alpaca", "Vicuna", "Mistral", "Mixtral",
            "Gemma", "Phi", "Qwen", "Baichuan", "Llama", "3", "Falcon", "MPT", "StarCoder", "CodeLlama", "SQLCoder",
            "Mistral", "7B", "Mixtral", "8x7B", "fine-tuning", "LoRA", "Low-Rank", "Adaptation", "QLoRA", "PEFT",
            "Parameter-Efficient", "Fine-Tuning", "prompt", "engineering", "in-context", "learning", "few-shot",
            "learning", "one-shot", "learning", "zero-shot", "learning", "chain-of-thought", "CoT", "reasoning",
            "tree-of-thought", "ToT", "graph-of-thought", "GoT", "retrieval-augmented", "generation", "RAG",
            "retrieval", "augmented", "generation", "vector", "database", "vector", "store", "embedding", "similarity",
            "search", "approximate", "nearest", "neighbor", "ANN", "search", "FAISS", "Pinecone", "Chroma", "Weaviate",
            "Milvus", "Qdrant", "pgvector", "elasticsearch", "solr", "lucene", "BM25", "TF-IDF", "term", "frequency",
            "inverse", "document", "frequency", "bag-of-words", "BoW", "n-gram", "tokenization", "tokenizer",
            "subword", "tokenization", "Byte", "Pair", "Encoding", "BPE", "WordPiece", "SentencePiece", "Unigram",
            "lemmatization", "stemming", "stopword", "removal", "text", "cleaning", "text", "preprocessing", "text",
            "normalization", "case", "folding", "Unicode", "normalization", "NFKC", "NFKD", "NFD", "NFC", "named",
            "entity", "recognition", "NER", "part-of-speech", "tagging", "POS", "tagging", "dependency", "parsing",
            "constituency", "parsing", "semantic", "role", "labeling", "SRL", "coreference", "resolution", "relation",
            "extraction", "event", "extraction", "text", "classification", "sentiment", "analysis", "topic", "modeling",
            "Latent", "Dirichlet", "Allocation", "LDA", "Non-negative", "Matrix", "Factorization", "NMF", "Latent",
            "Semantic", "Analysis", "LSA", "singular", "value", "decomposition", "SVD", "word", "embedding", "Word2Vec",
            "GloVe", "fastText", "ELMo", "BERT", "embedding", "sentence", "embedding", "paragraph", "embedding",
            "document", "embedding", "contextual", "embedding", "static", "embedding", "dynamic", "embedding",
            "multimodal", "embedding", "cross-modal", "embedding", "contrastive", "learning", "contrastive", "loss",
            "triplet", "loss", "margin", "loss", "softmax", "loss", "cross-entropy", "loss", "binary", "cross-entropy",
            "categorical", "cross-entropy", "sparse", "categorical", "cross-entropy", "focal", "loss", "Dice", "loss",
            "IoU", "loss", "Jaccard", "loss", "Tversky", "loss", "Lovasz", "loss", "Hinge", "loss", "Squared", "hinge",
            "loss", "Huber", "loss", "MAE", "loss", "MSE", "loss", "RMSE", "loss", "L1", "loss", "L2", "loss",
            "smooth", "L1", "loss", "quantile", "loss", "pinball", "loss", "Kullback-Leibler", "divergence", "KL",
            "divergence", "Jensen-Shannon", "divergence", "JS", "divergence", "Earth", "Mover's", "distance", "Wasserstein",
            "distance", "Cosine", "similarity", "Cosine", "distance", "Euclidean", "distance", "Manhattan", "distance",
            "Chebyshev", "distance", "Minkowski", "distance", "Hamming", "distance", "Jaccard", "similarity", "Jaccard",
            "distance", "Dice", "similarity", "Dice", "distance", "Overlap", "coefficient", "Sorensen-Dice", "coefficient",
            "Tanimoto", "coefficient", "Roberts", "coefficient", "Kappa", "coefficient", "Matthews", "correlation",
            "coefficient", "MCC", "phi", "coefficient", "Cramer's", "V", "Theil's", "U", "Goodman-Kruskal", "lambda",
            "Kendall's", "tau", "Spearman's", "rho", "Pearson", "correlation", "coefficient", "r", "covariance",
            "ANOVA", "t-test", "chi-square", "test", "F-test", "Mann-Whitney", "U", "test", "Wilcoxon", "signed-rank",
            "test", "Kruskal-Wallis", "test", "Friedman", "test", "post-hoc", "test", "Tukey's", "HSD", "test",
            "Bonferroni", "correction", "Holm", "correction", "Benjamini-Hochberg", "procedure", "false", "discovery",
            "rate", "FDR", "p-value", "confidence", "interval", "CI", "significance", "level", "alpha", "type", "I",
            "error", "type", "II", "error", "power", "effect", "size", "Cohen's", "d", "Cohen's", "h", "Cohen's", "f",
            "odds", "ratio", "OR", "relative", "risk", "RR", "hazard", "ratio", "HR", "absolute", "risk", "reduction",
            "ARR", "relative", "risk", "reduction", "RRR", "number", "needed", "to", "treat", "NNT", "number", "needed",
            "to", "harm", "NNH", "sensitivity", "specificity", "true", "positive", "rate", "TPR", "true", "negative",
            "rate", "TNR", "false", "positive", "rate", "FPR", "false", "negative", "rate", "FNR", "positive", "predictive",
            "value", "PPV", "negative", "predictive", "value", "NPV", "area", "under", "the", "curve", "AUC", "ROC",
            "curve", "precision-recall", "curve", "PR", "curve", "F1", "score", "F-beta", "score", "Jaccard", "index",
            "Dice", "coefficient", "IoU", "Intersection", "over", "Union", "accuracy", "error", "rate", "misclassification",
            "rate", "balanced", "accuracy", "macro-averaging", "micro-averaging", "weighted", "averaging", "sample",
            "averaging", "stratified", "sampling", "random", "sampling", "bootstrap", "sampling", "cross-validation",
            "k-fold", "stratified", "k-fold", "group", "k-fold", "time", "series", "split", "leave-one-out", "LOOCV",
            "train-test", "split", "training", "set", "validation", "set", "test", "set", "holdout", "set", "development",
            "set", "dev", "set", "gold", "standard", "ground", "truth", "label", "annotation", "ground", "truth", "label",
            "true", "positive", "TP", "true", "negative", "TN", "false", "positive", "FP", "false", "negative", "FN",
            "confusion", "matrix", "error", "matrix", "heatmap", "correlation", "matrix", "covariance", "matrix",
            "adjacency", "matrix", "incidence", "matrix", "laplacian", "matrix", "transition", "matrix", "probability",
            "matrix", "kernel", "matrix", "Gram", "matrix", "Hessian", "matrix", "Jacobian", "matrix", "Fisher",
            "information", "matrix", "covariance", "matrix", "precision", "matrix", "correlation", "matrix", "design",
            "matrix", "feature", "matrix", "data", "matrix", "observation", "matrix", "X", "matrix", "y", "vector",
            "target", "vector", "response", "vector", "dependent", "variable", "independent", "variable", "feature",
            "variable", "predictor", "variable", "explanatory", "variable", "covariate", "confounder", "mediator",
            "moderator", "interaction", "effect", "main", "effect", "simple", "effect", "conditional", "effect", "marginal",
            "effect", "average", "treatment", "effect", "ATE", "average", "treatment", "effect", "on", "the", "treated",
            "ATT", "local", "average", "treatment", "effect", "LATE", "intent-to-treat", "effect", "ITT", "complier",
            "average", "causal", "effect", "CACE", "causal", "effect", "causal", "inference", "causal", "discovery",
            "do-calculus", "backdoor", "criterion", "frontdoor", "criterion", "instrumental", "variable", "IV", "regression",
            "discontinuity", "design", "RDD", "difference-in-differences", "DiD", "propensity", "score", "matching",
            "PSM", "propensity", "score", "weighting", "IPW", "inverse", "probability", "weighting", "doubly", "robust",
            "estimation", "ATE", "estimation", "heterogeneous", "treatment", "effect", "HTE", "conditional", "average",
            "treatment", "effect", "CATE", "individual", "treatment", "effect", "ITE", "causal", "graph", "structural",
            "causal", "model", "SCM", "structural", "equation", "model", "SEM", "potential", "outcome", "framework",
            "Rubin", "causal", "model", "ignorability", "unconfoundedness", "exchangeability", "positivity", "overlap",
            "consistency", "SUTVA", "stable", "unit", "treatment", "value", "assumption", "ignorable", "treatment",
            "assignment", "conditional", "independence", "assumption", "CIA", "selection", "bias", "omitted", "variable",
            "bias", "confounding", "bias", "collider", "bias", "M-bias", "collider", "stratification", "bias", "descendant",
            "bias", "measurement", "error", "classical", "measurement", "error", "non-classical", "measurement", "error",
            "differential", "measurement", "error", "non-differential", "measurement", "error", "attenuation", "bias",
            "regression", "dilution", "bias", "selection", "bias", "attrition", "bias", "survivorship", "bias", "publication",
            "bias", "p-hacking", "data", "dredging", "multiple", "comparisons", "problem", "look-elsewhere", "effect",
            "Texas", "sharpshooter", "fallacy", "circular", "reasoning", "begging", "the", "question", "post", "hoc",
            "ergo", "propter", "hoc", "cum", "hoc", "ergo", "propter", "hoc", "regression", "to", "the", "mean", "RTM",
            "Gelman", "phenomenon", "law", "of", "large", "numbers", "LLN", "central", "limit", "theorem", "CLT", "Chebyshev's",
            "inequality", "Markov's", "inequality", "Jensen's", "inequality", "Hoeffding's", "inequality", "Chernoff",
            "bound", "McDiarmid's", "inequality", "Azuma", "inequality", "Doob", "martingale", "optional", "stopping",
            "theorem", "Brownian", "motion", "Wiener", "process", "martingale", "local", "martingale", "stopping", "time",
            "filtration", "sigma", "algebra", "measurable", "space", "measure", "space", "probability", "space", "sample",
            "space", "event", "sigma", "algebra", "Borel", "sigma", "algebra", "Lebesgue", "measure", "probability", "measure",
            "random", "variable", "discrete", "random", "variable", "continuous", "random", "variable", "mixed", "random",
            "variable", "probability", "mass", "function", "PMF", "probability", "density", "function", "PDF", "cumulative",
            "distribution", "function", "CDF", "survival", "function", "hazard", "function", "moment-generating", "function",
            "MGF", "characteristic", "function", "expectation", "expected", "value", "mean", "variance", "standard", "deviation",
            "skewness", "kurtosis", "moment", "raw", "moment", "central", "moment", "standardized", "moment", "covariance",
            "correlation", "independence", "conditional", "independence", "conditional", "probability", "conditional", "expectation",
            "law", "of", "total", "probability", "law", "of", "total", "expectation", "tower", "property", "iterated", "expectation",
            "Markov", "chain", "MC", "discrete-time", "Markov", "chain", "DTMC", "continuous-time", "Markov", "chain", "CTMC",
            "state", "space", "transition", "probability", "transition", "matrix", "transition", "rate", "matrix", "generator",
            "matrix", "stationary", "distribution", "steady-state", "distribution", "limiting", "distribution", "ergodic", "theorem",
            "reversible", "Markov", "chain", "detailed", "balance", "equations", "birth-death", "process", "Poisson", "process",
            "homogeneous", "Poisson", "process", "non-homogeneous", "Poisson", "process", "compound", "Poisson", "process",
            "renewal", "process", "renewal", "function", "renewal", "equation", "elementary", "renewal", "theorem", "key",
            "renewal", "theorem", "Blackwell's", "renewal", "theorem", "queueing", "theory", "M/M/1", "queue", "M/M/c",
            "queue", "M/G/1", "queue", "G/M/1", "queue", "Little's", "law", "PASTA", "property", "Poisson", "Arrivals",
            "See", "Time", "Averages", "birth-death", "queue", "Jackson", "network", "Gordon-Newell", "network", "BCMP",
            "network", "Kelly", "network", "product-form", "solution", "reversibility", "quasi-reversibility", "insensitivity",
            "robus"
        }

    def _load_model(self):
        if self.nlp is None:
            try:
                self.nlp = spacy.load(self.model_name)
            except OSError:
                self.nlp = spacy.load("en_core_web_sm")

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-]', ' ', text)
        return text.strip()

    def _is_valid_entity(self, text: str) -> bool:
        if not text or len(text) < 2 or len(text) > 50:
            return False
        if text.isdigit():
            return False
        if text.lower() in self._stopwords:
            return False
        if re.match(r'^[_\-]+$', text):
            return False
        if re.match(r'^[0-9]+\s*[A-Za-z]+$', text):
            return False
        return True

    def extract_entities_from_papers(
        self,
        papers: List[Paper],
        min_count: int = 2
    ) -> Dict[str, Entity]:
        self._load_model()
        
        entity_counts = defaultdict(int)
        entity_papers = defaultdict(set)
        
        for paper in papers:
            text_parts = []
            if paper.title:
                text_parts.append(paper.title)
            if paper.abstract:
                text_parts.append(paper.abstract)
            
            text = " ".join(text_parts)
            text = self._clean_text(text)
            
            if not text:
                continue
            
            doc = self.nlp(text)
            
            for ent in doc.ents:
                entity_text = ent.text.strip().lower()
                entity_text = re.sub(r'^[_\-]+|[_\-]+$', '', entity_text)
                entity_text = re.sub(r'\s+', ' ', entity_text)
                
                if self._is_valid_entity(entity_text):
                    entity_counts[entity_text] += 1
                    entity_papers[entity_text].add(paper.paper_id)
            
            for token in doc:
                if token.pos_ in ["NOUN", "PROPN"]:
                    lemma = token.lemma_.lower()
                    if self._is_valid_entity(lemma):
                        entity_counts[lemma] += 1
                        entity_papers[lemma].add(paper.paper_id)
        
        entities = {}
        for name, count in entity_counts.items():
            if count >= min_count:
                entities[name] = Entity(
                    name=name,
                    count=count,
                    papers=list(entity_papers[name])
                )
        
        return entities

    def extract_entities_from_text(
        self,
        text: str
    ) -> List[str]:
        self._load_model()
        
        text = self._clean_text(text)
        if not text:
            return []
        
        doc = self.nlp(text)
        
        entities = set()
        
        for ent in doc.ents:
            entity_text = ent.text.strip().lower()
            entity_text = re.sub(r'^[_\-]+|[_\-]+$', '', entity_text)
            entity_text = re.sub(r'\s+', ' ', entity_text)
            
            if self._is_valid_entity(entity_text):
                entities.add(entity_text)
        
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"]:
                lemma = token.lemma_.lower()
                if self._is_valid_entity(lemma):
                    entities.add(lemma)
        
        return list(entities)

    def build_cooccurrence_matrix(
        self,
        papers: List[Paper],
        entities: Dict[str, Entity],
        window_size: int = 10
    ) -> Dict[str, Dict[str, int]]:
        self._load_model()
        
        cooccurrence = defaultdict(lambda: defaultdict(int))
        entity_set = set(entities.keys())
        
        for paper in papers:
            text_parts = []
            if paper.title:
                text_parts.append(paper.title)
            if paper.abstract:
                text_parts.append(paper.abstract)
            
            text = " ".join(text_parts)
            text = self._clean_text(text)
            
            if not text:
                continue
            
            doc = self.nlp(text)
            
            words = []
            for token in doc:
                lemma = token.lemma_.lower()
                if lemma in entity_set:
                    words.append(lemma)
                else:
                    words.append(None)
            
            for i in range(len(words)):
                if words[i] is None:
                    continue
                
                start = max(0, i - window_size)
                end = min(len(words), i + window_size + 1)
                
                for j in range(start, end):
                    if i == j or words[j] is None:
                        continue
                    
                    if words[i] < words[j]:
                        cooccurrence[words[i]][words[j]] += 1
                    elif words[i] > words[j]:
                        cooccurrence[words[j]][words[i]] += 1
        
        return {k: dict(v) for k, v in cooccurrence.items()}


entity_extractor = EntityExtractor()
