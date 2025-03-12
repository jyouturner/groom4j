# Java Package Semantic Analysis

## Task Description
You are a world-class software architect analyzing a Java package structure. Your task is to synthesize a comprehensive understanding of this package based on the semantic analysis of its files and subpackages, with special focus on inter-component relationships and data flows.

## Package Information

Package Name: {package_name}

### Sub-packages Analysis:
{subpackage_notes}

### Direct Files Analysis:
{file_notes}

## Analysis Instructions

Analyze this package to extract both its semantic meaning and the relationships between its components:

1. Identify the package's overall purpose and architectural role
2. Map key components and their interactions within the package
3. Identify how data flows through the package components
4. Detect architectural patterns and design decisions
5. Analyze how this package relates to other packages in the system
6. Document service orchestration and processing sequences
7. Identify integration points with external systems
8. Note cross-cutting concerns and how they're implemented

## Response Format

Provide your analysis in the following JSON structure:

```json
{{
  "package_name": "full.package.name",
  "primary_purpose": "Main responsibility of the package",
  "architectural_role": "Role in system architecture (e.g., API layer, Domain layer, Infrastructure)",
  
  "key_components": [
    {{
      "name": "Component/Class name",
      "type": "Type (e.g., Service, Repository, Model)",
      "responsibility": "What this component does"
    }}
  ],
  
  "component_relationships": [
    {{
      "source": "SourceComponent",
      "target": "TargetComponent",
      "relationship_type": "calls/uses/creates/configures",
      "data_exchanged": "What data flows between these components",
      "context": "When/why this interaction occurs"
    }}
  ],
  
  "data_flows": [
    {{
      "description": "Description of a key data flow through the package",
      "flow_steps": [
        {{
          "component": "ComponentName",
          "action": "What happens to the data here",
          "transformation": "How data is transformed or enriched"
        }}
      ],
      "input_type": "Type of data entering this flow",
      "output_type": "Type of data exiting this flow"
    }}
  ],
  
  "design_patterns": [
    {{
      "pattern": "Pattern name",
      "implementation": "How it's implemented in this package",
      "components_involved": ["ComponentA", "ComponentB"]
    }}
  ],
  
  "package_boundaries": {{
    "incoming_interfaces": [
      {{
        "name": "Interface/endpoint name",
        "purpose": "What functionality it exposes to other packages",
        "consumers": ["Known consumers of this interface"]
      }}
    ],
    "outgoing_dependencies": [
      {{
        "target": "External package/system",
        "usage": "How and why this package uses the external dependency",
        "criticality": "How critical this dependency is (high/medium/low)"
      }}
    ]
  }},
  
  "dependencies": {{
    "internal": ["List of key internal dependencies"],
    "external": ["List of key external dependencies"]
  }},
  
  "service_orchestration": [
    {{
      "orchestrator": "Component that coordinates the process",
      "process_name": "Name of business/technical process",
      "sequence": [
        {{
          "step": 1,
          "service": "Service called",
          "purpose": "Why this call happens at this point"
        }}
      ],
      "conditional_branches": [
        {{
          "condition": "When this condition is true",
          "alternate_flow": "What happens instead"
        }}
      ]
    }}
  ],
  
  "cross_cutting_concerns": [
    {{
      "concern": "Security/Logging/Transactions/etc",
      "implementation": "How this concern is addressed",
      "components_affected": ["Components implementing this concern"]
    }}
  ],
  
  "package_structure": {{
    "organization": "How code is organized in this package",
    "rationale": "Why it's organized this way",
    "cohesion_assessment": "How well components belong together (high/medium/low)"
  }},
  
  "architectural_insights": [
    "Key architectural observations about this package",
    "Important design decisions evident in the implementation",
    "Potential architectural constraints or technical debt"
  ]
}}