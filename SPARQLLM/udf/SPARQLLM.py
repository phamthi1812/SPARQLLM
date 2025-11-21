import rdflib
from rdflib import Graph, ConjunctiveGraph, Dataset,  URIRef, Literal, Namespace
from rdflib.plugins.sparql.evaluate import (
    evalGraph,
    evalServiceQuery,
    evalLazyJoin,
    evalExtend,
    evalPart
)
from rdflib.plugins.sparql.evalutils import _eval
from rdflib.plugins.sparql.sparql import SPARQLError

import logging

# ============ GGF Detection Helper ============
def is_ggf_function(expr):
    """
    Detect if an expression is a Graph Generating Function (GGF) call.

    GGFs have URIs starting with:
    - http://ggf.org/  (canonical GGF namespace)
    - http://example.org/  (legacy/alias namespace)

    Args:
        expr: SPARQL expression (CompValue)

    Returns:
        bool: True if expression is a GGF function call
    """
    if hasattr(expr, 'name') and expr.name == 'Function':
        iri = expr.get('iri')
        if iri:
            iri_str = str(iri)
            return (iri_str.startswith('http://ggf.org/') or
                    iri_str.startswith('http://example.org/'))
    return False

# ============ Custom Evaluators ============
def my_evalextend(ctx, part):
    """
    Custom Extend evaluator for GGF functions.

    Forces eager evaluation when BIND contains a GGF call.
    This ensures named graphs are materialized before GRAPH clauses need them.

    Pattern: BIND(ggf:FUNC(...) AS ?g) GRAPH ?g {...}

    Args:
        ctx: Query context
        part: Extend CompValue with .expr, .var, .p

    Yields:
        FrozenBindings with ?g bound to named graph URI
    """
    # Check if this BIND contains a GGF call
    if is_ggf_function(part.expr):
        # Eager evaluation path for GGF functions
        logging.debug(f"GGF Extend detected: {part.expr.get('iri')}")

        # Evaluate sub-pattern (typically empty BGP)
        for c in evalPart(ctx, part.p):
            try:
                # Force immediate evaluation of GGF function
                # This materializes the named graph into global store
                result = _eval(part.expr, c.forget(ctx, _except=part._vars))

                if isinstance(result, SPARQLError):
                    raise result

                # Bind result to variable (?g)
                yield c.merge({part.var: result})

            except SPARQLError:
                # On error, yield binding without the variable
                yield c
    else:
        # Non-GGF path: delegate to default lazy evaluator
        # This preserves standard SPARQL behavior
        for binding in evalExtend(ctx, part):
            yield binding

def my_evaljoin(ctx, part):
    #print(f"EVALJOIN ctx: {ctx}, part: {part}")
    ## only lazyJoin. Sure to have the named graphs computed before evaluating graph clauses...
    return evalLazyJoin(ctx, part)

def my_evalgraph(ctx, part):
    print(f"EVALGRAPH ctx: {ctx.graph.identifier}, part: {part}")
#    try:
#        print(f"before init bindings: {ctx.initBindings}")
#        print(f"before bindings: {ctx.bindings}")
#        print(f"EVALGRAPH before solution: {ctx.solution()}")
#    except:
#        print("eval graph no bindings")
#        pass
    res=evalGraph(ctx, part)
#    try:
#        print(f"after init bindings: {ctx.initBindings}")
#        print(f"after graph bindings: {ctx.bindings}")
#        print(f"EVALGRAPH AFTER solution: {ctx.solution()}")
#    except:
#        print("EVALGRAPH after graph no bindings")
#        pass

    return res

def my_evalservice(ctx, part):
    print(f"EVALSERVICE ctx: {ctx}, part: {part}")
    return evalServiceQuery(ctx, part)


def customEval(ctx, part):  # noqa: N802
    """
    Custom evaluator for SPARQLLM GGF patterns.

    Intercepts specific algebra patterns to ensure eager evaluation:
    - Join: Forces evaluation order for nested patterns
    - Extend: Forces GGF function execution before GRAPH clauses

    Non-GGF queries fall through to default RDFlib evaluation.
    """
    if part.name == "Join":
        return my_evaljoin(ctx, part)

    if part.name == "Extend":
        return my_evalextend(ctx, part)

    # Other patterns (Graph, BGP, etc.) use default evaluators
    raise NotImplementedError()

rdflib.plugins.sparql.CUSTOM_EVALS["exampleEval"] = customEval

## super important !!
## need one store per request as graph are created dynamically during query execution.
store = Dataset()

def reset_store():
    """Reset the global store."""
    global store
    for g in list(store.contexts()):
        store.remove_graph(g)
    #store = Dataset()  # Reinitialize the global store