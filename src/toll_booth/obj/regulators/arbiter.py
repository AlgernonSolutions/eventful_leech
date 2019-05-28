from typing import Union, List, Tuple, Dict

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.regulators import ObjectRegulator, EdgeRegulator
from toll_booth.obj.schemata.rules import VertexLinkRuleEntry
from toll_booth.obj.schemata.schema import Schema
from toll_booth.obj.schemata.schema_entry import SchemaEdgeEntry, SchemaVertexEntry


class RuleArbiter:
    """

    """
    def __init__(self,
                 source_vertex: VertexData,
                 schema: Schema,
                 schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry]):
        self._schema_entry = schema_entry
        self._schema = schema
        self._rules = schema_entry.rules
        self._source_vertex = source_vertex

    @property
    def source_vertex(self):
        return self._source_vertex

    @property
    def schema(self):
        return self._schema

    @property
    def schema_entry(self):
        return self._schema_entry

    def process_rules(self, extracted_data: Dict) -> List[Tuple[VertexData, VertexLinkRuleEntry]]:
        """

        Args:
            extracted_data:

        Returns:

        """
        vertexes = []
        linking_rules = self._rules.linking_rules
        for rule_set in linking_rules:
            vertex_specifiers = rule_set.vertex_specifiers
            # TODO implement vertex testing
            if not self.test_vertex_specifiers(extracted_data, vertex_specifiers):
                continue
            for rule_entry in rule_set.rules:
                executor = ArbiterExecutor(self, rule_entry)
                vertexes.append(executor.generate_potential_vertexes(extracted_data))
        return vertexes

    @staticmethod
    def test_vertex_specifiers(extracted_data, vertex_specifiers):
        return True


class ArbiterExecutor:
    """

    """
    def __init__(self,
                 rule_arbiter: RuleArbiter,
                 rule_entry: VertexLinkRuleEntry):
        self._rule_arbiter = rule_arbiter
        self._source_vertex = rule_arbiter.source_vertex
        self._rule_entry = rule_entry
        self._target_type = rule_entry.target_type
        rule_schema_entry = rule_arbiter.schema[self._target_type]
        regulator = ObjectRegulator(rule_schema_entry)
        if hasattr(rule_entry, 'edge_label'):
            regulator = EdgeRegulator(rule_schema_entry)
        self._regulator = regulator

    @property
    def is_stub(self):
        return self._rule_entry.is_stub

    @property
    def if_missing(self):
        return self._rule_entry.if_absent

    def generate_potential_vertexes(self,
                                    extracted_data: Dict) -> Tuple[VertexData, VertexLinkRuleEntry]:
        """

        Args:
            extracted_data:

        Returns:

        """
        target_specifiers = self._rule_entry.target_specifiers
        target_constants = self.derive_target_constants(self._rule_entry.target_constants)
        specifiers = {}
        for specifier_executor in target_specifiers:
            specifier_kwargs = {
                'extracted_data': extracted_data,
                'rule_entry': self._rule_entry,
                'target_constants': target_constants,
                'source_vertex': self._source_vertex,
                'specifier': specifier_executor
            }
            generated_specifiers = specifier_executor.generate_specifiers(**specifier_kwargs)
            for generated_specifier in generated_specifiers:
                specifiers.update(generated_specifier)
        specified_vertex = self._regulator.create_potential_vertex_data(specifiers)
        return specified_vertex, self._rule_entry

    def derive_target_constants(self, target_constants: List[Dict]) -> Dict[str, str]:
        """

        Args:
            target_constants:

        Returns:

        """
        derived_constants = {}
        for target_constant in target_constants:
            constant_name, constant_value = self._derive_target_constant(**target_constant)
            derived_constants[constant_name] = constant_value
        return derived_constants

    def _derive_target_constant(self, constant_name, constant_value) -> Tuple[str, str]:
        """

        Args:
            constant_name:
            constant_value:

        Returns:

        """
        if "source." in constant_value:
            source_field_name = constant_value.split('.')[1]
            constant_value = self._source_vertex[source_field_name]
        return constant_name, constant_value
