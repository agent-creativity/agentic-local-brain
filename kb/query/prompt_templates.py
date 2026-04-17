"""
Configurable prompt template management for RAG.

This module provides a flexible system for managing and customizing
RAG prompt templates, supporting multiple built-in templates and
user-defined custom templates via configuration.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Built-in templates
BUILTIN_TEMPLATES = {
    "general": (
        "You are a knowledgeable assistant. Answer the user's question based on the provided context from their personal knowledge base. "
        "If the context doesn't contain enough information, say so honestly. "
        "Always cite your sources using [Source N] notation when referencing specific information.\n\n"
        "{topic_context}"
        "{entity_context}"
        "## Context\n{context}\n\n"
        "{conversation_history}"
        "Answer the following question concisely and accurately:\n{question}"
    ),
    "technical": (
        "You are a technical expert assistant. Provide precise, detailed technical answers based on the provided context. "
        "Use code examples when relevant. Cite sources with [Source N] notation.\n\n"
        "{topic_context}"
        "{entity_context}"
        "## Technical Context\n{context}\n\n"
        "{conversation_history}"
        "Technical question:\n{question}"
    ),
    "academic": (
        "You are an academic research assistant. Provide thorough, well-structured answers with proper citations. "
        "Analyze the evidence critically and note any limitations. Use [Source N] for citations.\n\n"
        "{topic_context}"
        "{entity_context}"
        "## Research Context\n{context}\n\n"
        "{conversation_history}"
        "Research question:\n{question}"
    ),
    "creative": (
        "You are a creative knowledge assistant. Synthesize information from the provided context in an engaging, "
        "insightful way. Draw connections between ideas. Cite sources with [Source N].\n\n"
        "{topic_context}"
        "{entity_context}"
        "## Context\n{context}\n\n"
        "{conversation_history}"
        "Question:\n{question}"
    ),
}


class PromptTemplateManager:
    """Manages prompt templates for RAG generation.
    
    This class provides a centralized way to manage prompt templates,
    supporting built-in templates and user-defined templates loaded
    from configuration.
    
    Usage example:
        >>> from kb.query.prompt_templates import PromptTemplateManager
        >>> config = {"query": {"rag": {"templates": {"default": "technical"}}}}
        >>> manager = PromptTemplateManager(config)
        >>> prompt = manager.render(context="...", question="What is Python?")
    
    Attributes:
        templates: Dictionary of template name to template string
        default_template: Name of the default template to use
    """

    def __init__(self, config: dict) -> None:
        """Initialize with config dict.
        
        Merges built-in templates with user-defined templates from config.
        
        Args:
            config: Configuration dictionary containing query.rag.templates section
        """
        self.config = config
        rag_config = config.get('query', {}).get('rag', {})
        templates_config = rag_config.get('templates', {})
        self.default_template = templates_config.get('default', 'general')
        
        # Merge built-in with user-defined templates
        self.templates = dict(BUILTIN_TEMPLATES)
        for name, template in templates_config.items():
            if name != 'default' and isinstance(template, str):
                self.templates[name] = template
                logger.debug(f"Loaded custom template: {name}")
        
        logger.info(
            f"PromptTemplateManager initialized with {len(self.templates)} templates, "
            f"default: {self.default_template}"
        )

    def get_template(self, name: Optional[str] = None) -> str:
        """Get a prompt template by name. Falls back to default.
        
        Args:
            name: Template name to retrieve. If None, uses default template.
            
        Returns:
            The template string
            
        Raises:
            KeyError: If template name is not found (should not happen with fallback)
        """
        template_name = name or self.default_template
        
        if template_name not in self.templates:
            logger.warning(
                f"Template '{template_name}' not found, falling back to 'general'"
            )
            template_name = 'general'
        
        return self.templates.get(template_name, BUILTIN_TEMPLATES['general'])

    def render(self, template_name: Optional[str] = None, **kwargs) -> str:
        """Render a template with variables.
        
        Supported variables:
        - context: The retrieval context text
        - question: The user's question
        - conversation_history: Formatted conversation history (optional)
        - entity_context: Entity context information (optional)
        - topic_context: Topic context information (optional)
        
        Args:
            template_name: Optional template name to use. Falls back to default.
            **kwargs: Variables to substitute in the template
            
        Returns:
            The rendered prompt string
        """
        template = self.get_template(template_name)
        
        # Fill in variables, use empty string for missing ones
        defaults = {
            'context': '',
            'question': '',
            'conversation_history': '',
            'entity_context': '',
            'topic_context': '',
        }
        defaults.update(kwargs)
        
        # Format topic_context and entity_context as sections if present
        if defaults['topic_context']:
            defaults['topic_context'] = f"## Topic Context\n{defaults['topic_context']}\n\n"
        if defaults['entity_context']:
            defaults['entity_context'] = f"## Related Entities\n{defaults['entity_context']}\n\n"
        if defaults['conversation_history']:
            defaults['conversation_history'] = f"## Previous Conversation\n{defaults['conversation_history']}\n\n"
        
        try:
            return template.format(**defaults)
        except KeyError as e:
            logger.warning(f"Template variable not found: {e}, using general template")
            return BUILTIN_TEMPLATES['general'].format(**defaults)

    def list_templates(self) -> Dict[str, str]:
        """List available template names with preview (first 100 chars).
        
        Returns:
            Dictionary mapping template name to truncated preview
        """
        return {
            name: tmpl[:100] + '...' if len(tmpl) > 100 else tmpl
            for name, tmpl in self.templates.items()
        }
