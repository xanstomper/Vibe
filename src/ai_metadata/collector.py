"""
Vibe AI Metadata System

Provides AI-readable metadata for code analysis and generation
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk levels for modules"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplexityLevel(Enum):
    """Complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class AIMetadata:
    """Comprehensive AI-readable metadata"""
    
    # Core metadata
    module_name: str = ""
    intent: List[str] = field(default_factory=list)
    owner: str = ""
    risk: RiskLevel = RiskLevel.LOW
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # What depends on this
    
    # API surface
    public_functions: List['FunctionMetadata'] = field(default_factory=list)
    public_types: List['TypeMetadata'] = field(default_factory=list)
    public_constants: List['ConstantMetadata'] = field(default_factory=list)
    
    # Code metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    technical_debt: float = 0.0
    
    # Testing
    test_coverage: float = 0.0
    test_count: int = 0
    last_test_run: str = ""
    
    # Quality
    documentation_coverage: float = 0.0
    lint_issues: int = 0
    security_issues: int = 0
    
    # AI-specific
    ai_suggestions: List[str] = field(default_factory=list)
    ai_confidence: float = 0.0
    ai_last_analyzed: str = ""
    
    # Relationships
    related_modules: List[str] = field(default_factory=list)
    similar_patterns: List[str] = field(default_factory=list)


@dataclass
class FunctionMetadata:
    """Function-level metadata"""
    name: str
    signature: str
    docstring: Optional[str] = None
    parameters: List['ParameterMetadata'] = field(default_factory=list)
    return_type: str = ""
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    side_effects: bool = False
    is_async: bool = False
    is_pure: bool = False
    test_coverage: float = 0.0
    call_count: int = 0
    
    # AI-specific
    ai_understanding: str = ""
    ai_suggestions: List[str] = field(default_factory=list)


@dataclass
class ParameterMetadata:
    """Parameter metadata"""
    name: str
    type: str
    description: Optional[str] = None
    default_value: Optional[str] = None
    is_mutable: bool = False
    constraints: List[str] = field(default_factory=list)


@dataclass
class TypeMetadata:
    """Type metadata"""
    name: str
    kind: str  # "struct", "enum", "trait", "type_alias"
    fields: List['FieldMetadata'] = field(default_factory=list)
    methods: List[FunctionMetadata] = field(default_factory=list)
    docstring: Optional[str] = None
    
    # AI-specific
    ai_description: str = ""
    ai_usage_examples: List[str] = field(default_factory=list)


@dataclass
class FieldMetadata:
    """Struct field metadata"""
    name: str
    type: str
    is_mutable: bool = False
    default_value: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class ConstantMetadata:
    """Constant metadata"""
    name: str
    type: str
    value: str
    docstring: Optional[str] = None


@dataclass
class ProjectMetadata:
    """Project-wide metadata"""
    name: str = ""
    version: str = ""
    description: str = ""
    authors: List[str] = field(default_factory=list)
    license: str = ""
    
    # Module graph
    modules: Dict[str, AIMetadata] = field(default_factory=dict)
    module_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    
    # Project metrics
    total_lines: int = 0
    total_modules: int = 0
    total_functions: int = 0
    total_types: int = 0
    
    # Quality metrics
    overall_coverage: float = 0.0
    overall_complexity: float = 0.0
    documentation_score: float = 0.0
    
    # AI insights
    ai_insights: List[str] = field(default_factory=list)
    ai_recommendations: List[str] = field(default_factory=list)
    architecture_patterns: List[str] = field(default_factory=list)


class MetadataCollector:
    """Collects and manages AI metadata"""
    
    def __init__(self):
        self.project_metadata = ProjectMetadata()
        self.current_module: Optional[AIMetadata] = None
    
    def start_module(self, name: str):
        """Start collecting metadata for a module"""
        self.current_module = AIMetadata(module_name=name)
        self.project_metadata.modules[name] = self.current_module
    
    def set_intent(self, *intents: str):
        """Set module intent"""
        if self.current_module:
            self.current_module.intent.extend(intents)
    
    def set_owner(self, owner: str):
        """Set module owner"""
        if self.current_module:
            self.current_module.owner = owner
    
    def set_risk(self, risk: RiskLevel):
        """Set risk level"""
        if self.current_module:
            self.current_module.risk = risk
    
    def add_dependency(self, dep: str):
        """Add a dependency"""
        if self.current_module:
            self.current_module.dependencies.append(dep)
    
    def add_function(self, func: FunctionMetadata):
        """Add a function to the metadata"""
        if self.current_module:
            self.current_module.public_functions.append(func)
            self.project_metadata.total_functions += 1
    
    def add_type(self, typ: TypeMetadata):
        """Add a type to the metadata"""
        if self.current_module:
            self.current_module.public_types.append(typ)
            self.project_metadata.total_types += 1
    
    def add_constant(self, const: ConstantMetadata):
        """Add a constant to the metadata"""
        if self.current_module:
            self.current_module.public_constants.append(const)
    
    def set_metrics(self, loc: int, cyclomatic: int, cognitive: int):
        """Set code metrics"""
        if self.current_module:
            self.current_module.lines_of_code = loc
            self.current_module.cyclomatic_complexity = cyclomatic
            self.current_module.cognitive_complexity = cognitive
    
    def set_test_coverage(self, coverage: float, test_count: int):
        """Set test coverage"""
        if self.current_module:
            self.current_module.test_coverage = coverage
            self.current_module.test_count = test_count
    
    def add_ai_suggestion(self, suggestion: str):
        """Add an AI suggestion"""
        if self.current_module:
            self.current_module.ai_suggestions.append(suggestion)
    
    def finish_module(self):
        """Finish collecting metadata for current module"""
        self.current_module = None
    
    def generate_index(self) -> Dict[str, Any]:
        """Generate a searchable index of all metadata"""
        index = {
            "modules": {},
            "functions": {},
            "types": {},
            "dependencies": {},
            "risk_assessment": {},
        }
        
        for module_name, metadata in self.project_metadata.modules.items():
            # Index module
            index["modules"][module_name] = {
                "intent": metadata.intent,
                "owner": metadata.owner,
                "risk": metadata.risk.value,
                "loc": metadata.lines_of_code,
                "complexity": metadata.cyclomatic_complexity,
            }
            
            # Index functions
            for func in metadata.public_functions:
                index["functions"][f"{module_name}.{func.name}"] = {
                    "signature": func.signature,
                    "complexity": func.complexity.value,
                    "coverage": func.test_coverage,
                }
            
            # Index types
            for typ in metadata.public_types:
                index["types"][f"{module_name}.{typ.name}"] = {
                    "kind": typ.kind,
                    "fields": len(typ.fields),
                    "methods": len(typ.methods),
                }
            
            # Index dependencies
            index["dependencies"][module_name] = metadata.dependencies
            
            # Risk assessment
            index["risk_assessment"][module_name] = {
                "level": metadata.risk.value,
                "complexity": metadata.cyclomatic_complexity,
                "coverage": metadata.test_coverage,
                "debt": metadata.technical_debt,
            }
        
        return index
    
    def generate_report(self) -> str:
        """Generate a human-readable report"""
        report = []
        report.append("# Vibe Project Analysis Report\n")
        
        # Summary
        report.append("## Summary\n")
        report.append(f"- Total Modules: {self.project_metadata.total_modules}")
        report.append(f"- Total Functions: {self.project_metadata.total_functions}")
        report.append(f"- Total Types: {self.project_metadata.total_types}")
        report.append(f"- Total Lines: {self.project_metadata.total_lines}")
        report.append("")
        
        # Module details
        report.append("## Modules\n")
        for name, metadata in self.project_metadata.modules.items():
            report.append(f"### {name}\n")
            report.append(f"- **Intent:** {', '.join(metadata.intent)}")
            report.append(f"- **Owner:** {metadata.owner}")
            report.append(f"- **Risk:** {metadata.risk.value}")
            report.append(f"- **Lines:** {metadata.lines_of_code}")
            report.append(f"- **Complexity:** {metadata.cyclomatic_complexity}")
            report.append(f"- **Test Coverage:** {metadata.test_coverage}%")
            
            if metadata.ai_suggestions:
                report.append("- **AI Suggestions:**")
                for suggestion in metadata.ai_suggestions:
                    report.append(f"  - {suggestion}")
            report.append("")
        
        # Risk assessment
        report.append("## Risk Assessment\n")
        for name, metadata in self.project_metadata.modules.items():
            if metadata.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                report.append(f"- **{name}**: {metadata.risk.value} risk")
                if metadata.test_coverage < 80:
                    report.append(f"  - Low test coverage: {metadata.test_coverage}%")
                if metadata.cyclomatic_complexity > 10:
                    report.append(f"  - High complexity: {metadata.cyclomatic_complexity}")
        
        return "\n".join(report)
    
    def to_json(self) -> str:
        """Export metadata as JSON"""
        return json.dumps(self.project_metadata.__dict__, indent=2, default=str)
    
    def to_vibe_metadata(self) -> str:
        """Generate Vibe metadata syntax"""
        lines = []
        
        for name, metadata in self.project_metadata.modules.items():
            lines.append(f"module {name}")
            lines.append("")
            
            if metadata.intent:
                lines.append("intent:")
                for intent in metadata.intent:
                    lines.append(f"    {intent}")
            
            if metadata.owner:
                lines.append(f"owner: {metadata.owner}")
            
            if metadata.risk != RiskLevel.LOW:
                lines.append(f"risk: {metadata.risk.value}")
            
            if metadata.dependencies:
                lines.append("dependencies:")
                for dep in metadata.dependencies:
                    lines.append(f"    - {dep}")
            
            lines.append("")
        
        return "\n".join(lines)


def collect_metadata_from_ast(program, source: str) -> AIMetadata:
    """Collect metadata from parsed AST"""
    collector = MetadataCollector()
    
    if program.module:
        collector.start_module(program.module.name)
        
        # Extract metadata from module declaration
        metadata = program.module.metadata
        if metadata:
            collector.set_intent(*metadata.intent)
            if metadata.owner:
                collector.set_owner(metadata.owner)
            if metadata.risk:
                risk_map = {
                    "low": RiskLevel.LOW,
                    "medium": RiskLevel.MEDIUM,
                    "high": RiskLevel.HIGH,
                    "critical": RiskLevel.CRITICAL,
                }
                collector.set_risk(risk_map.get(metadata.risk, RiskLevel.LOW))
            
            for dep in metadata.dependencies:
                collector.add_dependency(dep)
    
    # Calculate metrics
    loc = source.count('\n') + 1
    collector.set_metrics(loc, 0, 0)  # Simplified
    
    if collector.current_module:
        collector.finish_module()
    
    return collector.project_metadata.modules.get(
        program.module.name if program.module else "",
        AIMetadata()
    )


def generate_ai_context(metadata: AIMetadata) -> str:
    """Generate AI context string for code generation"""
    context_parts = []
    
    context_parts.append(f"Module: {metadata.module_name}")
    context_parts.append(f"Intent: {', '.join(metadata.intent)}")
    context_parts.append(f"Owner: {metadata.owner}")
    context_parts.append(f"Risk Level: {metadata.risk.value}")
    
    if metadata.public_functions:
        context_parts.append("\nPublic Functions:")
        for func in metadata.public_functions:
            context_parts.append(f"  - {func.name}: {func.signature}")
    
    if metadata.public_types:
        context_parts.append("\nPublic Types:")
        for typ in metadata.public_types:
            context_parts.append(f"  - {typ.name}: {typ.kind}")
    
    if metadata.dependencies:
        context_parts.append(f"\nDependencies: {', '.join(metadata.dependencies)}")
    
    return "\n".join(context_parts)
