"""Account and node management scenarios.

Tests for the FEBE account() and create_node() operations:
- account(): Set the current account for document creation (opcode 34)
- create_node(): Create a new node/account and return its address (opcode 38)

Xanadu tumbler structure: Node.0.User.0.Doc.0.Element
- Nodes are server/storage locations
- Accounts are user identities within nodes
- Documents are created under accounts
"""

from client import (
    Address, Offset, Span, SpecSet, VSpec,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL
)
from .common import vspec_to_dict, specset_to_list, DEFAULT_ACCOUNT


def scenario_account_set(session):
    """Set the current account and create a document under it."""
    # Set account (already done by test harness, but verify explicitly)
    account = Address(1, 1, 0, 1)
    session.account(account)

    # Create document under this account
    docid = session.create_document()

    return {
        "name": "account_set",
        "description": "Set account and verify documents are created under it",
        "operations": [
            {"op": "account", "account": str(account)},
            {"op": "create_document", "result": str(docid),
             "comment": "Document should be under account 1.1.0.1"}
        ]
    }


def scenario_account_switch(session):
    """Switch between accounts and verify document addresses.

    Documents created after account() are placed under the current account.
    """
    # First account
    account1 = Address(1, 1, 0, 1)
    session.account(account1)
    doc1 = session.create_document()

    # Switch to different account
    account2 = Address(1, 1, 0, 2)
    session.account(account2)
    doc2 = session.create_document()

    # Switch back and create another
    session.account(account1)
    doc3 = session.create_document()

    return {
        "name": "account_switch",
        "description": "Switch between accounts and verify document addresses",
        "operations": [
            {"op": "account", "account": str(account1)},
            {"op": "create_document", "result": str(doc1),
             "comment": "First doc under account 1.1.0.1"},
            {"op": "account", "account": str(account2)},
            {"op": "create_document", "result": str(doc2),
             "comment": "First doc under account 1.1.0.2"},
            {"op": "account", "account": str(account1)},
            {"op": "create_document", "result": str(doc3),
             "comment": "Second doc under account 1.1.0.1"}
        ]
    }


def scenario_create_node(session):
    """Create a new node and verify the returned address."""
    # Create a node under the current account context
    account = Address(1, 1, 0, 1)
    session.account(account)

    # create_node returns the address of the new node
    new_node = session.create_node(account)

    return {
        "name": "create_node",
        "description": "Create a new node and observe its address",
        "operations": [
            {"op": "account", "account": str(account)},
            {"op": "create_node", "account": str(account), "result": str(new_node)}
        ]
    }


def scenario_create_multiple_nodes(session):
    """Create multiple nodes and verify sequential addressing."""
    account = Address(1, 1, 0, 1)
    session.account(account)

    # Create several nodes
    node1 = session.create_node(account)
    node2 = session.create_node(account)
    node3 = session.create_node(account)

    return {
        "name": "create_multiple_nodes",
        "description": "Create multiple nodes and observe address progression",
        "operations": [
            {"op": "account", "account": str(account)},
            {"op": "create_node", "account": str(account), "result": str(node1)},
            {"op": "create_node", "account": str(account), "result": str(node2)},
            {"op": "create_node", "account": str(account), "result": str(node3)}
        ]
    }


def scenario_node_then_documents(session):
    """Create a node, then create documents under it.

    This tests the workflow of establishing a new namespace
    and then populating it with documents.
    """
    # Start with base account
    base_account = Address(1, 1, 0, 1)
    session.account(base_account)

    # Create a new node
    new_node = session.create_node(base_account)

    # Switch to the new node/account and create documents
    session.account(new_node)
    doc1 = session.create_document()
    doc2 = session.create_document()

    # Populate one of the documents
    opened = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Content in new node"])
    vspanset = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)
    session.close_document(opened)

    return {
        "name": "node_then_documents",
        "description": "Create node, switch to it, create and populate documents",
        "operations": [
            {"op": "account", "account": str(base_account)},
            {"op": "create_node", "account": str(base_account), "result": str(new_node)},
            {"op": "account", "account": str(new_node),
             "comment": "Switch to newly created node"},
            {"op": "create_document", "result": str(doc1)},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc1), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "Content in new node"},
            {"op": "retrieve_contents", "result": contents},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_documents_single_account(session):
    """Create multiple documents under the same account.

    Verifies sequential document creation and addressing.
    """
    # Create documents under the default account
    account = Address(1, 1, 0, 1)
    session.account(account)

    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["First document"])
    vspanset1 = session.retrieve_vspanset(opened1)
    specset1 = SpecSet(VSpec(opened1, list(vspanset1.spans)))
    contents1 = session.retrieve_contents(specset1)
    session.close_document(opened1)

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Second document"])
    vspanset2 = session.retrieve_vspanset(opened2)
    specset2 = SpecSet(VSpec(opened2, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)
    session.close_document(opened2)

    return {
        "name": "documents_single_account",
        "description": "Create multiple documents under the same account",
        "operations": [
            {"op": "account", "account": str(account)},
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "result": str(opened1)},
            {"op": "insert", "text": "First document"},
            {"op": "retrieve_contents", "result": contents1},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "result": str(opened2)},
            {"op": "insert", "text": "Second document"},
            {"op": "retrieve_contents", "result": contents2},
            {"op": "close_document", "doc": str(opened2)}
        ]
    }


SCENARIOS = [
    ("accounts", "account_set", scenario_account_set),
    ("accounts", "account_switch", scenario_account_switch),
    ("accounts", "create_node", scenario_create_node),
    ("accounts", "create_multiple_nodes", scenario_create_multiple_nodes),
    ("accounts", "node_then_documents", scenario_node_then_documents),
    ("accounts", "documents_single_account", scenario_documents_single_account),
]
