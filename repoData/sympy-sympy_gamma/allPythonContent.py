__FILENAME__ = diffsteps
import sympy
import collections

import stepprinter
from stepprinter import functionnames, replace_u_var

from sympy.core.function import AppliedUndef
from sympy.functions.elementary.trigonometric import TrigonometricFunction
from sympy.strategies.core import switch, identity
def Rule(name, props=""):
    return collections.namedtuple(name, props + " context symbol")

ConstantRule = Rule("ConstantRule", "number")
ConstantTimesRule = Rule("ConstantTimesRule", "constant other substep")
PowerRule = Rule("PowerRule", "base exp")
AddRule = Rule("AddRule", "substeps")
MulRule = Rule("MulRule", "terms substeps")
DivRule = Rule("DivRule", "numerator denominator numerstep denomstep")
ChainRule = Rule("ChainRule", "substep inner u_var innerstep")
TrigRule = Rule("TrigRule", "f")
ExpRule = Rule("ExpRule", "f base")
LogRule = Rule("LogRule", "arg base")
FunctionRule = Rule("FunctionRule")
AlternativeRule = Rule("AlternativeRule", "alternatives")
DontKnowRule = Rule("DontKnowRule")
RewriteRule = Rule("RewriteRule", "rewritten substep")

DerivativeInfo = collections.namedtuple('DerivativeInfo', 'expr symbol')

evaluators = {}
def evaluates(rule):
    def _evaluates(func):
        func.rule = rule
        evaluators[rule] = func
        return func
    return _evaluates

def power_rule(derivative):
    expr, symbol = derivative.expr, derivative.symbol
    base, exp = expr.as_base_exp()

    if not base.has(symbol):
        if isinstance(exp, sympy.Symbol):
            return ExpRule(expr, base, expr, symbol)
        else:
            u = sympy.Dummy()
            f = base ** u
            return ChainRule(
                ExpRule(f, base, f, u),
                exp, u,
                diff_steps(exp, symbol),
                expr, symbol
            )
    elif not exp.has(symbol):
        if isinstance(base, sympy.Symbol):
            return PowerRule(base, exp, expr, symbol)
        else:
            u = sympy.Dummy()
            f = u ** exp
            return ChainRule(
                PowerRule(u, exp, f, u),
                base, u,
                diff_steps(base, symbol),
                expr, symbol
            )
    else:
        return DontKnowRule(expr, symbol)

def add_rule(derivative):
    expr, symbol = derivative.expr, derivative.symbol
    return AddRule([diff_steps(arg, symbol) for arg in expr.args],
                   expr, symbol)

def constant_rule(derivative):
    expr, symbol = derivative.expr, derivative.symbol
    return ConstantRule(expr, expr, symbol)

def mul_rule(derivative):
    expr, symbol = derivative
    terms = expr.args
    is_div = 1 / sympy.Wild("denominator")

    coeff, f = expr.as_independent(symbol)

    if coeff != 1:
        return ConstantTimesRule(coeff, f, diff_steps(f, symbol), expr, symbol)

    numerator, denominator = expr.as_numer_denom()
    if denominator != 1:
        return DivRule(numerator, denominator,
                       diff_steps(numerator, symbol),
                       diff_steps(denominator, symbol), expr, symbol)

    return MulRule(terms, [diff_steps(g, symbol) for g in terms], expr, symbol)

def trig_rule(derivative):
    expr, symbol = derivative
    arg = expr.args[0]

    default = TrigRule(expr, expr, symbol)
    if not isinstance(arg, sympy.Symbol):
        u = sympy.Dummy()
        default = ChainRule(
            TrigRule(expr.func(u), expr.func(u), u),
            arg, u, diff_steps(arg, symbol),
            expr, symbol)

    if isinstance(expr, (sympy.sin, sympy.cos)):
        return default
    elif isinstance(expr, sympy.tan):
        f_r = sympy.sin(arg) / sympy.cos(arg)

        return AlternativeRule([
            default,
            RewriteRule(f_r, diff_steps(f_r, symbol), expr, symbol)
        ], expr, symbol)
    elif isinstance(expr, sympy.csc):
        f_r = 1 / sympy.sin(arg)

        return AlternativeRule([
            default,
            RewriteRule(f_r, diff_steps(f_r, symbol), expr, symbol)
        ], expr, symbol)
    elif isinstance(expr, sympy.sec):
        f_r = 1 / sympy.cos(arg)

        return AlternativeRule([
            default,
            RewriteRule(f_r, diff_steps(f_r, symbol), expr, symbol)
        ], expr, symbol)
    elif isinstance(expr, sympy.cot):
        f_r_1 = 1 / sympy.tan(arg)
        f_r_2 = sympy.cos(arg) / sympy.sin(arg)
        return AlternativeRule([
            default,
            RewriteRule(f_r_1, diff_steps(f_r_1, symbol), expr, symbol),
            RewriteRule(f_r_2, diff_steps(f_r_2, symbol), expr, symbol)
        ], expr, symbol)
    else:
        return DontKnowRule(f, symbol)

def exp_rule(derivative):
    expr, symbol = derivative
    exp = expr.args[0]
    if isinstance(exp, sympy.Symbol):
        return ExpRule(expr, sympy.E, expr, symbol)
    else:
        u = sympy.Dummy()
        f = sympy.exp(u)
        return ChainRule(ExpRule(f, sympy.E, f, u),
                         exp, u, diff_steps(exp, symbol), expr, symbol)

def log_rule(derivative):
    expr, symbol = derivative
    arg = expr.args[0]
    if len(expr.args) == 2:
        base = expr.args[1]
    else:
        base = sympy.E
        if isinstance(arg, sympy.Symbol):
            return LogRule(arg, base, expr, symbol)
        else:
            u = sympy.Dummy()
            return ChainRule(LogRule(u, base, sympy.log(u, base), u),
                             arg, u, diff_steps(arg, symbol), expr, symbol)

def function_rule(derivative):
    return FunctionRule(derivative.expr, derivative.symbol)

@evaluates(ConstantRule)
def eval_constant(*args):
    return 0

@evaluates(ConstantTimesRule)
def eval_constanttimes(constant, other, substep, expr, symbol):
    return constant * diff(substep)

@evaluates(AddRule)
def eval_add(substeps, expr, symbol):
    results = [diff(step) for step in substeps]
    return sum(results)

@evaluates(DivRule)
def eval_div(numer, denom, numerstep, denomstep, expr, symbol):
    d_numer = diff(numerstep)
    d_denom = diff(denomstep)
    return (denom * d_numer - numer * d_denom) / (denom **2)

@evaluates(ChainRule)
def eval_chain(substep, inner, u_var, innerstep, expr, symbol):
    return diff(substep).subs(u_var, inner) * diff(innerstep)

@evaluates(PowerRule)
@evaluates(ExpRule)
@evaluates(LogRule)
@evaluates(DontKnowRule)
@evaluates(FunctionRule)
def eval_default(*args):
    func, symbol = args[-2], args[-1]

    if isinstance(func, sympy.Symbol):
        func = sympy.Pow(func, 1, evaluate=False)

    # Automatically derive and apply the rule (don't use diff() directly as
    # chain rule is a separate step)
    substitutions = []
    mapping = {}
    constant_symbol = sympy.Dummy()
    for arg in func.args:
        if symbol in arg.free_symbols:
            mapping[symbol] = arg
            substitutions.append(symbol)
        else:
            mapping[constant_symbol] = arg
            substitutions.append(constant_symbol)

    rule = func.func(*substitutions).diff(symbol)
    return rule.subs(mapping)

@evaluates(MulRule)
def eval_mul(terms, substeps, expr, symbol):
    diffs = map(diff, substeps)

    result = sympy.S.Zero
    for i in range(len(terms)):
        subresult = diffs[i]
        for index, term in enumerate(terms):
            if index != i:
                subresult *= term
        result += subresult
    return result

@evaluates(TrigRule)
def eval_default_trig(*args):
    return sympy.trigsimp(eval_default(*args))

@evaluates(RewriteRule)
def eval_rewrite(rewritten, substep, expr, symbol):
    return diff(substep)

@evaluates(AlternativeRule)
def eval_alternative(alternatives, expr, symbol):
    return diff(alternatives[1])

def diff_steps(expr, symbol):
    deriv = DerivativeInfo(expr, symbol)

    def key(deriv):
        expr = deriv.expr
        if isinstance(expr, TrigonometricFunction):
            return TrigonometricFunction
        elif isinstance(expr, AppliedUndef):
            return AppliedUndef
        elif not expr.has(symbol):
            return 'constant'
        else:
            return expr.func

    return switch(key, {
        sympy.Pow: power_rule,
        sympy.Symbol: power_rule,
        sympy.Dummy: power_rule,
        sympy.Add: add_rule,
        sympy.Mul: mul_rule,
        TrigonometricFunction: trig_rule,
        sympy.exp: exp_rule,
        sympy.log: log_rule,
        AppliedUndef: function_rule,
        'constant': constant_rule
    })(deriv)

def diff(rule):
    try:
        return evaluators[rule.__class__](*rule)
    except KeyError:
        raise ValueError("Cannot evaluate derivative")

class DiffPrinter(object):
    def __init__(self, rule):
        self.print_rule(rule)
        self.rule = rule

    def print_rule(self, rule):
        if isinstance(rule, PowerRule):
            self.print_Power(rule)
        elif isinstance(rule, ChainRule):
            self.print_Chain(rule)
        elif isinstance(rule, ConstantRule):
            self.print_Number(rule)
        elif isinstance(rule, ConstantTimesRule):
            self.print_ConstantTimes(rule)
        elif isinstance(rule, AddRule):
            self.print_Add(rule)
        elif isinstance(rule, MulRule):
            self.print_Mul(rule)
        elif isinstance(rule, DivRule):
            self.print_Div(rule)
        elif isinstance(rule, TrigRule):
            self.print_Trig(rule)
        elif isinstance(rule, ExpRule):
            self.print_Exp(rule)
        elif isinstance(rule, LogRule):
            self.print_Log(rule)
        elif isinstance(rule, DontKnowRule):
            self.print_DontKnow(rule)
        elif isinstance(rule, AlternativeRule):
            self.print_Alternative(rule)
        elif isinstance(rule, RewriteRule):
            self.print_Rewrite(rule)
        elif isinstance(rule, FunctionRule):
            self.print_Function(rule)
        else:
            self.append(repr(rule))

    def print_Power(self, rule):
        with self.new_step():
            self.append("Apply the power rule: {0} goes to {1}".format(
                self.format_math(rule.context),
                self.format_math(diff(rule))))

    def print_Number(self, rule):
        with self.new_step():
            self.append("The derivative of the constant {} is zero.".format(
                self.format_math(rule.number)))

    def print_ConstantTimes(self, rule):
        with self.new_step():
            self.append("The derivative of a constant times a function "
                        "is the constant times the derivative of the function.")
            with self.new_level():
                self.print_rule(rule.substep)
            self.append("So, the result is: {}".format(
                self.format_math(diff(rule))))

    def print_Add(self, rule):
        with self.new_step():
            self.append("Differentiate {} term by term:".format(
                self.format_math(rule.context)))
            with self.new_level():
                for substep in rule.substeps:
                    self.print_rule(substep)
            self.append("The result is: {}".format(
                self.format_math(diff(rule))))

    def print_Mul(self, rule):
        with self.new_step():
            self.append("Apply the product rule:".format(
                self.format_math(rule.context)))

            fnames = map(lambda n: sympy.Function(n)(rule.symbol),
                         functionnames(len(rule.terms)))
            derivatives = map(lambda f: sympy.Derivative(f, rule.symbol), fnames)
            ruleform = []
            for index in range(len(rule.terms)):
                buf = []
                for i in range(len(rule.terms)):
                    if i == index:
                        buf.append(derivatives[i])
                    else:
                        buf.append(fnames[i])
                ruleform.append(reduce(lambda a,b: a*b, buf))
            self.append(self.format_math_display(
                sympy.Eq(sympy.Derivative(reduce(lambda a,b: a*b, fnames),
                                        rule.symbol),
                       sum(ruleform))))

            for fname, deriv, term, substep in zip(fnames, derivatives,
                                                   rule.terms, rule.substeps):
                self.append("{}; to find {}:".format(
                    self.format_math(sympy.Eq(fname, term)),
                    self.format_math(deriv)
                ))
                with self.new_level():
                    self.print_rule(substep)

            self.append("The result is: " + self.format_math(diff(rule)))

    def print_Div(self, rule):
        with self.new_step():
            f, g = rule.numerator, rule.denominator
            fp, gp = f.diff(rule.symbol), g.diff(rule.symbol)
            x = rule.symbol
            ff = sympy.Function("f")(x)
            gg = sympy.Function("g")(x)
            qrule_left = sympy.Derivative(ff / gg, rule.symbol)
            qrule_right = sympy.ratsimp(sympy.diff(sympy.Function("f")(x) /
                                                   sympy.Function("g")(x)))
            qrule = sympy.Eq(qrule_left, qrule_right)
            self.append("Apply the quotient rule, which is:")
            self.append(self.format_math_display(qrule))
            self.append("{} and {}.".format(self.format_math(sympy.Eq(ff, f)),
                                            self.format_math(sympy.Eq(gg, g))))
            self.append("To find {}:".format(self.format_math(ff.diff(rule.symbol))))
            with self.new_level():
                self.print_rule(rule.numerstep)
            self.append("To find {}:".format(self.format_math(gg.diff(rule.symbol))))
            with self.new_level():
                self.print_rule(rule.denomstep)
            self.append("Now plug in to the quotient rule:")
            self.append(self.format_math(diff(rule)))

    def print_Chain(self, rule):
        with self.new_step(), self.new_u_vars() as (u, du):
            self.append("Let {}.".format(self.format_math(sympy.Eq(u, rule.inner))))
            self.print_rule(replace_u_var(rule.substep, rule.u_var, u))
        with self.new_step():
            if isinstance(rule.innerstep, FunctionRule):
                self.append(
                    "Then, apply the chain rule. Multiply by {}:".format(
                        self.format_math(
                            sympy.Derivative(rule.inner, rule.symbol))))
                self.append(self.format_math_display(diff(rule)))
            else:
                self.append(
                    "Then, apply the chain rule. Multiply by {}:".format(
                        self.format_math(
                            sympy.Derivative(rule.inner, rule.symbol))))
                with self.new_level():
                    self.print_rule(rule.innerstep)
                self.append("The result of the chain rule is:")
                self.append(self.format_math_display(diff(rule)))

    def print_Trig(self, rule):
        with self.new_step():
            if isinstance(rule.f, sympy.sin):
                self.append("The derivative of sine is cosine:")
            elif isinstance(rule.f, sympy.cos):
                self.append("The derivative of cosine is negative sine:")
            elif isinstance(rule.f, sympy.sec):
                self.append("The derivative of secant is secant times tangent:")
            elif isinstance(rule.f, sympy.csc):
                self.append("The derivative of cosecant is negative cosecant times cotangent:")
            self.append("{}".format(
                self.format_math_display(sympy.Eq(
                    sympy.Derivative(rule.f, rule.symbol),
                    diff(rule)))))

    def print_Exp(self, rule):
        with self.new_step():
            if rule.base == sympy.E:
                self.append("The derivative of {} is itself.".format(
                    self.format_math(sympy.exp(rule.symbol))))
            else:
                self.append(
                    self.format_math(sympy.Eq(sympy.Derivative(rule.f, rule.symbol),
                                            diff(rule))))

    def print_Log(self, rule):
        with self.new_step():
            if rule.base == sympy.E:
                self.append("The derivative of {} is {}.".format(
                    self.format_math(rule.context),
                    self.format_math(diff(rule))
                ))
            else:
                # This case shouldn't come up often, seeing as SymPy
                # automatically applies the change-of-base identity
                self.append("The derivative of {} is {}.".format(
                    self.format_math(sympy.log(rule.symbol, rule.base,
                                               evaluate=False)),
                    self.format_math(1/(rule.arg * sympy.ln(rule.base)))))
                self.append("So {}".format(
                    self.format_math(sympy.Eq(
                        sympy.Derivative(rule.context, rule.symbol),
                        diff(rule)))))

    def print_Alternative(self, rule):
        with self.new_step():
            self.append("There are multiple ways to do this derivative.")
            self.append("One way:")
            with self.new_level():
                self.print_rule(rule.alternatives[0])

    def print_Rewrite(self, rule):
        with self.new_step():
            self.append("Rewrite the function to be differentiated:")
            self.append(self.format_math_display(
                sympy.Eq(rule.context, rule.rewritten)))
            self.print_rule(rule.substep)

    def print_Function(self, rule):
        with self.new_step():
            self.append("Trivial:")
            self.append(self.format_math_display(
                sympy.Eq(sympy.Derivative(rule.context, rule.symbol),
                       diff(rule))))

    def print_DontKnow(self, rule):
        with self.new_step():
            self.append("Don't know the steps in finding this derivative.")
            self.append("But the derivative is")
            self.append(self.format_math_display(diff(rule)))

class HTMLPrinter(DiffPrinter, stepprinter.HTMLPrinter):
    def __init__(self, rule):
        self.alternative_functions_printed = set()
        stepprinter.HTMLPrinter.__init__(self)
        DiffPrinter.__init__(self, rule)

    def print_Alternative(self, rule):
        if rule.context.func in self.alternative_functions_printed:
            self.print_rule(rule.alternatives[0])
        elif len(rule.alternatives) == 2:
            self.alternative_functions_printed.add(rule.context.func)
            self.print_rule(rule.alternatives[1])
        else:
            self.alternative_functions_printed.add(rule.context.func)
            with self.new_step():
                self.append("There are multiple ways to do this derivative.")
                for index, r in enumerate(rule.alternatives[1:]):
                    with self.new_collapsible():
                        self.append_header("Method #{}".format(index + 1))
                        with self.new_level():
                            self.print_rule(r)

    def finalize(self):
        answer = diff(self.rule)
        if answer:
            simp = sympy.simplify(answer)
            if simp != answer:
                answer = simp
                with self.new_step():
                    self.append("Now simplify:")
                    self.append(self.format_math_display(simp))
        self.lines.append('</ol>')
        self.lines.append('<hr/>')
        self.level = 0
        self.append('The answer is:')
        self.append(self.format_math_display(answer))
        return '\n'.join(self.lines)

def print_html_steps(function, symbol):
    a = HTMLPrinter(diff_steps(function, symbol))
    return a.finalize()

########NEW FILE########
__FILENAME__ = intsteps
import sympy
import collections
from contextlib import contextmanager
import stepprinter
from stepprinter import functionnames, Rule, replace_u_var

from sympy.integrals.manualintegrate import (
    manualintegrate, _manualintegrate, integral_steps, evaluates,
    ConstantRule, ConstantTimesRule, PowerRule, AddRule, URule,
    PartsRule, CyclicPartsRule, TrigRule, ExpRule, LogRule, ArctanRule,
    AlternativeRule, DontKnowRule, RewriteRule
)

# Need this to break loops
# TODO: add manualintegrate flag to integrate
_evaluating = None
@evaluates(DontKnowRule)
def eval_dontknow(context, symbol):
    global _evaluating
    if _evaluating == context:
        return None
    _evaluating = context
    result = sympy.integrate(context, symbol)
    _evaluating = None
    return result


def contains_dont_know(rule):
    if isinstance(rule, DontKnowRule):
        return True
    else:
        for val in rule._asdict().values():
            if isinstance(val, tuple):
                if contains_dont_know(val):
                    return True
            elif isinstance(val, list):
                if any(contains_dont_know(i) for i in val):
                    return True
    return False

def filter_unknown_alternatives(rule):
    if isinstance(rule, AlternativeRule):
        alternatives = list(filter(lambda r: not contains_dont_know(r), rule.alternatives))
        if not alternatives:
            alternatives = rule.alternatives
        return AlternativeRule(alternatives, rule.context, rule.symbol)
    return rule

class IntegralPrinter(object):
    def __init__(self, rule):
        self.rule = rule
        self.print_rule(rule)
        self.u_name = 'u'
        self.u = self.du = None

    def print_rule(self, rule):
        if isinstance(rule, ConstantRule):
            self.print_Constant(rule)
        elif isinstance(rule, ConstantTimesRule):
            self.print_ConstantTimes(rule)
        elif isinstance(rule, PowerRule):
            self.print_Power(rule)
        elif isinstance(rule, AddRule):
            self.print_Add(rule)
        elif isinstance(rule, URule):
            self.print_U(rule)
        elif isinstance(rule, PartsRule):
            self.print_Parts(rule)
        elif isinstance(rule, CyclicPartsRule):
            self.print_CyclicParts(rule)
        elif isinstance(rule, TrigRule):
            self.print_Trig(rule)
        elif isinstance(rule, ExpRule):
            self.print_Exp(rule)
        elif isinstance(rule, LogRule):
            self.print_Log(rule)
        elif isinstance(rule, ArctanRule):
            self.print_Arctan(rule)
        elif isinstance(rule, AlternativeRule):
            self.print_Alternative(rule)
        elif isinstance(rule, DontKnowRule):
            self.print_DontKnow(rule)
        elif isinstance(rule, RewriteRule):
            self.print_Rewrite(rule)
        else:
            self.append(repr(rule))

    def print_Constant(self, rule):
        with self.new_step():
            self.append("The integral of a constant is the constant "
                        "times the variable of integration:")
            self.append(
                self.format_math_display(
                    sympy.Eq(sympy.Integral(rule.constant, rule.symbol),
                           _manualintegrate(rule))))

    def print_ConstantTimes(self, rule):
        with self.new_step():
            self.append("The integral of a constant times a function "
                        "is the constant times the integral of the function:")
            self.append(self.format_math_display(
                sympy.Eq(
                    sympy.Integral(rule.context, rule.symbol),
                    rule.constant * sympy.Integral(rule.other, rule.symbol))))

            with self.new_level():
                self.print_rule(rule.substep)
            self.append("So, the result is: {}".format(
                self.format_math(_manualintegrate(rule))))

    def print_Power(self, rule):
        with self.new_step():
            self.append("The integral of {} is {} when {}:".format(
                self.format_math(rule.symbol ** sympy.Symbol('n')),
                self.format_math((rule.symbol ** (1 + sympy.Symbol('n'))) /
                                 (1 + sympy.Symbol('n'))),
                self.format_math(sympy.Ne(sympy.Symbol('n'), -1)),
            ))
            self.append(
                self.format_math_display(
                    sympy.Eq(sympy.Integral(rule.context, rule.symbol),
                           _manualintegrate(rule))))

    def print_Add(self, rule):
        with self.new_step():
            self.append("Integrate term-by-term:")
            for substep in rule.substeps:
                with self.new_level():
                    self.print_rule(substep)
            self.append("The result is: {}".format(
                self.format_math(_manualintegrate(rule))))

    def print_U(self, rule):
        with self.new_step(), self.new_u_vars() as (u, du):
            # commutative always puts the symbol at the end when printed
            dx = sympy.Symbol('d' + rule.symbol.name, commutative=0)
            self.append("Let {}.".format(
                self.format_math(sympy.Eq(u, rule.u_func))))
            self.append("Then let {} and substitute {}:".format(
                self.format_math(sympy.Eq(du,rule.u_func.diff(rule.symbol) * dx)),
                self.format_math(rule.constant * du)
            ))

            integrand = rule.substep.context.subs(rule.u_var, u)
            self.append(self.format_math_display(
                sympy.Integral(integrand, u)))

            with self.new_level():
                self.print_rule(replace_u_var(rule.substep, rule.u_var, u))

            self.append("Now substitute {} back in:".format(
                self.format_math(u)))

            self.append(self.format_math_display(_manualintegrate(rule)))

    def print_Parts(self, rule):
        with self.new_step():
            self.append("Use integration by parts:")

            u, v, du, dv = map(lambda f: sympy.Function(f)(rule.symbol), 'u v du dv'.split())
            self.append(self.format_math_display(
                r"""\int \operatorname{u} \operatorname{dv}
                = \operatorname{u}\operatorname{v} -
                \int \operatorname{v} \operatorname{du}"""
            ))

            self.append("Let {} and let {}.".format(
                self.format_math(sympy.Eq(u, rule.u)),
                self.format_math(sympy.Eq(dv, rule.dv))
            ))
            self.append("Then {}.".format(
                self.format_math(sympy.Eq(du, rule.u.diff(rule.symbol)))
            ))

            self.append("To find {}:".format(self.format_math(v)))

            with self.new_level():
                self.print_rule(rule.v_step)

            self.append("Now evaluate the sub-integral.")
            self.print_rule(rule.second_step)

    def print_CyclicParts(self, rule):
        with self.new_step():
            self.append("Use integration by parts, noting that the integrand"
                        " eventually repeats itself.")

            u, v, du, dv = map(lambda f: sympy.Function(f)(rule.symbol), 'u v du dv'.split())
            current_integrand = rule.context
            total_result = sympy.S.Zero
            with self.new_level():

                sign = 1
                for rl in rule.parts_rules:
                    with self.new_step():
                        self.append("For the integrand {}:".format(self.format_math(current_integrand)))
                        self.append("Let {} and let {}.".format(
                            self.format_math(sympy.Eq(u, rl.u)),
                            self.format_math(sympy.Eq(dv, rl.dv))
                        ))

                        v_f, du_f = _manualintegrate(rl.v_step), rl.u.diff(rule.symbol)

                        total_result += sign * rl.u * v_f
                        current_integrand = v_f * du_f

                        self.append("Then {}.".format(
                            self.format_math(
                                sympy.Eq(
                                    sympy.Integral(rule.context, rule.symbol),
                                    total_result - sign * sympy.Integral(current_integrand, rule.symbol)))
                        ))
                        sign *= -1
                with self.new_step():
                    self.append("Notice that the integrand has repeated itself, so "
                                "move it to one side:")
                    self.append("{}".format(
                        self.format_math_display(sympy.Eq(
                            (1 - rule.coefficient) * sympy.Integral(rule.context, rule.symbol),
                            total_result
                        ))
                    ))
                    self.append("Therefore,")
                    self.append("{}".format(
                        self.format_math_display(sympy.Eq(
                            sympy.Integral(rule.context, rule.symbol),
                            _manualintegrate(rule)
                        ))
                    ))


    def print_Trig(self, rule):
        with self.new_step():
            text = {
                'sin': "The integral of sine is negative cosine:",
                'cos': "The integral of cosine is sine:",
                'sec*tan': "The integral of secant times tangent is secant:",
                'csc*cot': "The integral of cosecant times cotangent is cosecant:",
            }.get(rule.func)

            if text:
                self.append(text)

            self.append(self.format_math_display(
                sympy.Eq(sympy.Integral(rule.context, rule.symbol),
                       _manualintegrate(rule))))

    def print_Exp(self, rule):
        with self.new_step():
            if rule.base == sympy.E:
                self.append("The integral of the exponential function is itself.")
            else:
                self.append("The integral of an exponential function is itself"
                            " divided by the natural logarithm of the base.")
            self.append(self.format_math_display(
                sympy.Eq(sympy.Integral(rule.context, rule.symbol),
                       _manualintegrate(rule))))

    def print_Log(self, rule):
        with self.new_step():
            self.append("The integral of {} is {}.".format(
                self.format_math(1 / rule.func),
                self.format_math(_manualintegrate(rule))
            ))

    def print_Arctan(self, rule):
        with self.new_step():
            self.append("The integral of {} is {}.".format(
                self.format_math(1 / (1 + rule.symbol ** 2)),
                self.format_math(_manualintegrate(rule))
            ))

    def print_Rewrite(self, rule):
        with self.new_step():
            self.append("Rewrite the integrand:")
            self.append(self.format_math_display(
                sympy.Eq(rule.context, rule.rewritten)))
            self.print_rule(rule.substep)

    def print_DontKnow(self, rule):
        with self.new_step():
            self.append("Don't know the steps in finding this integral.")
            self.append("But the integral is")
            self.append(self.format_math_display(sympy.integrate(rule.context, rule.symbol)))


class HTMLPrinter(IntegralPrinter, stepprinter.HTMLPrinter):
    def __init__(self, rule):
        self.alternative_functions_printed = set()
        stepprinter.HTMLPrinter.__init__(self)
        IntegralPrinter.__init__(self, rule)

    def print_Alternative(self, rule):
        # TODO: make more robust
        rule = filter_unknown_alternatives(rule)

        if len(rule.alternatives) == 1:
            self.print_rule(rule.alternatives[0])
            return

        if rule.context.func in self.alternative_functions_printed:
            self.print_rule(rule.alternatives[0])
        else:
            self.alternative_functions_printed.add(rule.context.func)
            with self.new_step():
                self.append("There are multiple ways to do this integral.")
                for index, r in enumerate(rule.alternatives):
                    with self.new_collapsible():
                        self.append_header("Method #{}".format(index + 1))
                        with self.new_level():
                            self.print_rule(r)

    def format_math_constant(self, math):
        return '<script type="math/tex; mode=display">{}</script>'.format(
            sympy.latex(math) + r'+ \mathrm{constant}')

    def finalize(self):
        rule = filter_unknown_alternatives(self.rule)
        answer = _manualintegrate(rule)
        if answer:
            simp = sympy.simplify(sympy.trigsimp(answer))
            if simp != answer:
                answer = simp
                with self.new_step():
                    self.append("Now simplify:")
                    self.append(self.format_math_display(simp))
            with self.new_step():
                self.append("Add the constant of integration:")
                self.append(self.format_math_constant(answer))
        self.lines.append('</ol>')
        self.lines.append('<hr/>')
        self.level = 0
        self.append('The answer is:')
        self.append(self.format_math_constant(answer))
        return '\n'.join(self.lines)

def print_html_steps(function, symbol):
    rule = integral_steps(function, symbol)
    if isinstance(rule, DontKnowRule):
        raise ValueError("Cannot evaluate integral")
    a = HTMLPrinter(rule)
    return a.finalize()

########NEW FILE########
__FILENAME__ = logic
import sys
import traceback
import collections
from utils import Eval, latexify, arguments, removeSymPy, \
    custom_implicit_transformation, synonyms, OTHER_SYMPY_FUNCTIONS, \
    close_matches
from resultsets import find_result_set, get_card, format_by_type, \
    is_function_handled, find_learn_more_set
from sympy import latex, series, sympify, solve, Derivative, \
    Integral, Symbol, diff, integrate
import sympy
from sympy.core.function import FunctionClass
from sympy.parsing.sympy_parser import stringify_expr, eval_expr, \
    standard_transformations, convert_xor, TokenError

PREEXEC = """from __future__ import division
from sympy import *
import sympy
from sympy.solvers.diophantine import diophantine
"""


def mathjax_latex(*args):
    tex_code = []
    for obj in args:
        if hasattr(obj, 'as_latex'):
            tex_code.append(obj.as_latex())
        else:
            tex_code.append(latex(obj))

    tag = '<script type="math/tex; mode=display">'
    if len(args) == 1:
        obj = args[0]
        if (isinstance(obj, sympy.Basic) and
            not obj.free_symbols and not obj.is_Integer and
            not obj.is_Float and
            obj.is_finite is not False and
            hasattr(obj, 'evalf')):
            tag = '<script type="math/tex; mode=display" data-numeric="true" ' \
                  'data-output-repr="{}" data-approximation="{}">'.format(
                      repr(obj), latex(obj.evalf(15)))

    tex_code = ''.join(tex_code)

    return ''.join([tag, tex_code, '</script>'])


class SymPyGamma(object):

    def eval(self, s):
        result = None

        try:
            result = self.eval_input(s)
        except TokenError:
            return [
                {"title": "Input", "input": s},
                {"title": "Error", "input": s, "error": "Invalid input"}
            ]
        except Exception as e:
            return self.handle_error(s, e)

        if result:
            parsed, arguments, evaluator, evaluated = result

            cards = []

            close_match = close_matches(s, sympy.__dict__)
            if close_match:
                cards.append({
                    "ambiguity": close_match,
                    "description": ""
                })

            try:
                cards.extend(self.prepare_cards(parsed, arguments, evaluator, evaluated))
            except ValueError as e:
                return self.handle_error(s, e)

            return cards

    def handle_error(self, s, e):
        if isinstance(e, SyntaxError):
            error = {
                "msg": e.msg,
                "offset": e.offset
            }
            if e.text:
                error["input_start"] = e.text[:e.offset]
                error["input_end"] = e.text[e.offset:]
            return [
                {"title": "Input", "input": s},
                {"title": "Error", "input": s, "exception_info": error}
            ]
        elif isinstance(e, ValueError):
            return [
                {"title": "Input", "input": s},
                {"title": "Error", "input": s, "error": e.message}
            ]
        else:
            trace = traceback.format_exc()
            trace = ("There was an error in Gamma.\n"
                     "For reference, the stack trace is:\n\n" + trace)
            return [
                {"title": "Input", "input": s},
                {"title": "Error", "input": s, "error": trace}
            ]

    def disambiguate(self, arguments):
        if arguments[0] == 'factor':
            if arguments.args and isinstance(arguments.args[0], sympy.Number):
                return ('factorint({})'.format(arguments.args[0]),
                        "<var>factor</var> factors polynomials, while <var>factorint</var> factors integers.")
        return None

    def eval_input(self, s):
        namespace = {}
        exec PREEXEC in {}, namespace

        def plot(f=None, **kwargs):
            """Plot functions. Not the same as SymPy's plot.

            This plot function is specific to Gamma. It has the following syntax::

                plot([x^2, x^3, ...])

            or::

                plot(y=x,y1=x^2,r=sin(theta),r1=cos(theta))

            ``plot`` accepts either a list of single-variable expressions to
            plot or keyword arguments indicating expressions to plot. If
            keyword arguments are used, the plot will be polar if the keyword
            argument starts with ``r`` and will be an xy graph otherwise.

            Note that Gamma will cut off plot values above and below a
            certain value, and that it will **not** warn the user if so.

            """
            pass
        namespace.update({
            'plot': plot,  # prevent textplot from printing stuff
            'help': lambda f: f
        })

        evaluator = Eval(namespace)
        # change to True to spare the user from exceptions:
        if not len(s):
            return None

        transformations = []
        transformations.append(synonyms)
        transformations.extend(standard_transformations)
        transformations.extend((convert_xor, custom_implicit_transformation))
        parsed = stringify_expr(s, {}, namespace, transformations)
        try:
            evaluated = eval_expr(parsed, {}, namespace)
        except SyntaxError:
            raise
        except Exception as e:
            raise ValueError(str(e))
        input_repr = repr(evaluated)
        namespace['input_evaluated'] = evaluated

        return parsed, arguments(parsed, evaluator), evaluator, evaluated

    def get_cards(self, arguments, evaluator, evaluated):
        first_func_name = arguments[0]
        # is the top-level function call to a function such as factorint or
        # simplify?
        is_function = False
        # is the top-level function being called?
        is_applied = arguments.args or arguments.kwargs

        first_func = evaluator.get(first_func_name)
        is_function = (
            first_func and
            not isinstance(first_func, FunctionClass) and
            not isinstance(first_func, sympy.Atom) and
            first_func_name and first_func_name[0].islower() and
            not first_func_name in OTHER_SYMPY_FUNCTIONS)

        if is_applied:
            convert_input, cards = find_result_set(arguments[0], evaluated)
        else:
            convert_input, cards = find_result_set(None, evaluated)

        components = convert_input(arguments, evaluated)
        if 'input_evaluated' in components:
            evaluated = components['input_evaluated']

        evaluator.set('input_evaluated', evaluated)

        return components, cards, evaluated, (is_function and is_applied)

    def prepare_cards(self, parsed, arguments, evaluator, evaluated):
        components, cards, evaluated, is_function = self.get_cards(arguments, evaluator, evaluated)

        if is_function:
            latex_input = ''.join(['<script type="math/tex; mode=display">',
                                   latexify(parsed, evaluator),
                                   '</script>'])
        else:
            latex_input = mathjax_latex(evaluated)

        result = []

        ambiguity = self.disambiguate(arguments)
        if ambiguity:
            result.append({
                "ambiguity": ambiguity[0],
                "description": ambiguity[1]
            })

        result.append({
            "title": "SymPy",
            "input": removeSymPy(parsed),
            "output": latex_input
        })

        if cards:
            if any(get_card(c).is_multivariate() for c in cards):
                result[-1].update({
                    "num_variables": len(components['variables']),
                    "variables": map(repr, components['variables']),
                    "variable": repr(components['variable'])
                })

        # If no result cards were found, but the top-level call is to a
        # function, then add a special result card to show the result
        if not cards and not components['variable'] and is_function:
            result.append({
                'title': 'Result',
                'input': removeSymPy(parsed),
                'output': format_by_type(evaluated, arguments, mathjax_latex)
            })
        else:
            var = components['variable']

            # If the expression is something like 'lcm(2x, 3x)', display the
            # result of the function before the rest of the cards
            if is_function and not is_function_handled(arguments[0]):
                result.append(
                    {"title": "Result", "input": "",
                     "output": format_by_type(evaluated, arguments, mathjax_latex)})

            line = "simplify(input_evaluated)"
            simplified = evaluator.eval(line,
                                        use_none_for_exceptions=True,
                                        repr_expression=False)
            if (simplified != None and
                simplified != evaluated and
                arguments.args and
                len(arguments.args) > 0 and
                simplified != arguments.args[0]):
                result.append(
                    {"title": "Simplification", "input": repr(simplified),
                     "output": mathjax_latex(simplified)})
            elif arguments.function == 'simplify':
                result.append(
                    {"title": "Simplification", "input": "",
                     "output": mathjax_latex(evaluated)})

            for card_name in cards:
                card = get_card(card_name)

                if not card:
                    continue

                try:
                    result.append({
                        'card': card_name,
                        'var': repr(var),
                        'title': card.format_title(evaluated),
                        'input': card.format_input(repr(evaluated), components),
                        'pre_output': latex(
                            card.pre_output_function(evaluated, var)),
                        'parameters': card.card_info.get('parameters', [])
                    })
                except (SyntaxError, ValueError) as e:
                    pass

            if is_function:
                learn_more = find_learn_more_set(arguments[0])
                if learn_more:
                    result.append({
                        "title": "Learn More",
                        "input": '',
                        "output": learn_more
                    })
        return result

    def get_card_info(self, card_name, expression, variable):
        card = get_card(card_name)

        if not card:
            raise KeyError

        _, arguments, evaluator, evaluated = self.eval_input(expression)
        variable = sympy.Symbol(variable)
        components, cards, evaluated, _ = self.get_cards(arguments, evaluator, evaluated)
        components['variable'] = variable

        return {
            'var': repr(variable),
            'title': card.format_title(evaluated),
            'input': card.format_input(repr(evaluated), components),
            'pre_output': latex(card.pre_output_function(evaluated, variable))
        }

    def eval_card(self, card_name, expression, variable, parameters):
        card = get_card(card_name)

        if not card:
            raise KeyError

        _, arguments, evaluator, evaluated = self.eval_input(expression)
        variable = sympy.Symbol(variable)
        components, cards, evaluated, _ = self.get_cards(arguments, evaluator, evaluated)
        components['variable'] = variable
        evaluator.set(str(variable), variable)
        result = card.eval(evaluator, components, parameters)

        return {
            'value': repr(result),
            'output': card.format_output(result, mathjax_latex)
        }

########NEW FILE########
__FILENAME__ = nlcommand
prepositions = ['of', 'to', 'for']
articles = ['the']
pronouns = ['me']
modifiers = {
    'tell': 'show',
    'show': 'show',
    'find': 'show',
    'how': 'how',
    'steps': 'how'
}
modifier_priorities = {
    'show': 0,
    'how': 1
}
commands = {
    'derivative': 'differentiate',
    'differentiate': 'differentiate'
}
functions = {
    'differentiate': {
        'show': 'diff',
        'how': 'diffsteps',
        'default': 'diff'
    }
}

def extraneous(word):
    return (word in prepositions) or (word in pronouns) or (word in articles)

def interpret(command):
    words = filter(lambda word: not extraneous(word), command.lower().split())
    modifier = 'default'
    modifier_priority = -1
    cmds = []
    expressions = []
    expression = []

    for word in words:
        if word in modifiers:
            mod = modifiers[word]
            if modifier_priorities[mod] > modifier_priority:
                modifier = mod
                modifier_priority = modifier_priorities[mod]
            if expression:
                expressions.append(''.join(math))
        elif word in commands:
            cmds.append(commands[word])
            if expression:
                expressions.append(''.join(math))
        else:
            expression.append(word)
    if expression:
        expressions.append(' '.join(expression))
    for cmd in cmds:
        return functions[cmd][mod], expressions

########NEW FILE########
__FILENAME__ = resultsets
import sys
import json
import itertools
import sympy
from sympy.core.function import FunctionClass
from sympy.core.symbol import Symbol
import docutils.core
import diffsteps
import intsteps


class ResultCard(object):
    """
    Operations to generate a result card.

    title -- Title of the card

    result_statement -- Statement evaluated to get result

    pre_output_function -- Takes input expression and a symbol, returns a
    SymPy object
    """
    def __init__(self, title, result_statement, pre_output_function,
                 **kwargs):
        self.card_info = kwargs
        self.title = title
        self.result_statement = result_statement
        self.pre_output_function = pre_output_function

    def eval(self, evaluator, components, parameters=None):
        if parameters is None:
            parameters = {}
        else:
            parameters = parameters.copy()

        parameters = self.default_parameters(parameters)

        for component, val in components.items():
            parameters[component] = val

        variable = components['variable']

        line = self.result_statement.format(_var=variable, **parameters)
        line = line % 'input_evaluated'
        result = evaluator.eval(line, use_none_for_exceptions=True,
                                repr_expression=False)

        return result

    def format_input(self, input_repr, components, **parameters):
        if parameters is None:
            parameters = {}
        parameters = self.default_parameters(parameters)
        variable = components['variable']
        if 'format_input_function' in self.card_info:
            return self.card_info['format_input_function'](
                self.result_statement, input_repr, components)
        return self.result_statement.format(_var=variable, **parameters) % input_repr

    def format_output(self, output, formatter):
        if 'format_output_function' in self.card_info:
            return self.card_info['format_output_function'](output, formatter)
        return formatter(output)

    def format_title(self, input_evaluated):
        if self.card_info.get('format_title_function'):
            return self.card_info['format_title_function'](self.title,
                                                           input_evaluated)
        return self.title

    def is_multivariate(self):
        return self.card_info.get('multivariate', True)

    def default_parameters(self, kwargs):
        if 'parameters' in self.card_info:
            for arg in self.card_info['parameters']:
                kwargs.setdefault(arg, '')
        return kwargs

    def __repr__(self):
        return "<ResultCard '{}'>".format(self.title)


class FakeResultCard(ResultCard):
    """ResultCard whose displayed expression != actual code.

    Used when creating the result to be displayed involves code that a user
    would not normally need to do, e.g. calculating plot points (where a
    user would simply use ``plot``)."""

    def __init__(self, *args, **kwargs):
        super(FakeResultCard, self).__init__(*args, **kwargs)
        assert 'eval_method' in kwargs

    def eval(self, evaluator, components, parameters=None):
        if parameters is None:
            parameters = {}
        return self.card_info['eval_method'](evaluator, components, parameters)


class MultiResultCard(ResultCard):
    """Tries multiple statements and displays the first that works."""

    def __init__(self, title, *cards):
        super(MultiResultCard, self).__init__(title, '', lambda *args: '')
        self.cards = cards
        self.cards_used = []

    def eval(self, evaluator, components, parameters):
        self.cards_used = []
        results = []

        # TODO Implicit state is bad, come up with better API
        # in particular a way to store variable, cards used
        for card in self.cards:
            try:
                result = card.eval(evaluator, components, parameters)
            except ValueError:
                continue
            if result != None:
                if not any(result == r[1] for r in results):
                    self.cards_used.append(card)
                    results.append((card, result))
        if results:
            self.input_repr = evaluator.get("input_evaluated")
            self.components = components
            return results
        return "None"

    def format_input(self, input_repr, components):
        return None

    def format_output(self, output, formatter):
        if not isinstance(output, list):
            return output
        html = ["<ul>"]
        for card, result in output:
            html.append("<li>")
            html.append('<div class="cell_input">')
            html.append(card.format_input(self.input_repr, self.components))
            html.append('</div>')
            html.append(card.format_output(result, formatter))
            html.append("</li>")
        html.append("</ul>")
        return "\n".join(html)


# Decide which result card set to use

def is_derivative(input_evaluated):
    return isinstance(input_evaluated, sympy.Derivative)

def is_integral(input_evaluated):
    return isinstance(input_evaluated, sympy.Integral)

def is_integer(input_evaluated):
    return isinstance(input_evaluated, sympy.Integer)

def is_rational(input_evaluated):
    return isinstance(input_evaluated, sympy.Rational) and not input_evaluated.is_Integer

def is_float(input_evaluated):
    return isinstance(input_evaluated, sympy.Float)

def is_numbersymbol(input_evaluated):
    return isinstance(input_evaluated, sympy.NumberSymbol)

def is_constant(input_evaluated):
    # is_constant reduces trig identities (even with simplify=False?) so we
    # check free_symbols instead
    return (hasattr(input_evaluated, 'free_symbols') and
            not input_evaluated.free_symbols)

def is_approximatable_constant(input_evaluated):
    # is_constant, but exclude Integer/Float/infinity
    return (hasattr(input_evaluated, 'free_symbols') and
            not input_evaluated.free_symbols and
            not input_evaluated.is_Integer and
            not input_evaluated.is_Float and
            input_evaluated.is_finite is not True)

def is_complex(input_evaluated):
    try:
        return sympy.I in input_evaluated.atoms()
    except (AttributeError, TypeError):
        return False

def is_trig(input_evaluated):
    try:
        if (isinstance(input_evaluated, sympy.Basic) and
            any(input_evaluated.find(func)
                for func in (sympy.sin, sympy.cos, sympy.tan,
                             sympy.csc, sympy.sec, sympy.cot))):
            return True
    except AttributeError:
        pass
    return False

def is_not_constant_basic(input_evaluated):
    return (not is_constant(input_evaluated) and
            isinstance(input_evaluated, sympy.Basic) and
            not is_logic(input_evaluated))

def is_uncalled_function(input_evaluated):
    return hasattr(input_evaluated, '__call__') and not isinstance(input_evaluated, sympy.Basic)

def is_matrix(input_evaluated):
    return isinstance(input_evaluated, sympy.Matrix)

def is_logic(input_evaluated):
    return isinstance(input_evaluated, (sympy.And, sympy.Or, sympy.Not, sympy.Xor))

def is_sum(input_evaluated):
    return isinstance(input_evaluated, sympy.Sum)

def is_product(input_evaluated):
    return isinstance(input_evaluated, sympy.Product)


# Functions to convert input and extract variable used

def default_variable(arguments, evaluated):
    try:
        variables = list(evaluated.atoms(sympy.Symbol))
    except:
        variables = []

    return {
        'variables': variables,
        'variable': variables[0] if variables else None,
        'input_evaluated': evaluated
    }

def extract_first(arguments, evaluated):
    result = default_variable(arguments, evaluated)
    result['input_evaluated'] = arguments[1][0]
    return result

def extract_integral(arguments, evaluated):
    limits = arguments[1][1:]
    variables = []

    if not limits:
        variables = [arguments[1][0].atoms(sympy.Symbol).pop()]
        limits = variables
    else:
        for limit in limits:
            if isinstance(limit, tuple):
                variables.append(limit[0])
            else:
                variables.append(limit)

    return {
        'integrand': arguments[1][0],
        'variables': variables,
        'variable': variables[0],
        'limits': limits
    }

def extract_derivative(arguments, evaluated):
    variables = list(sorted(arguments[1][0].atoms(sympy.Symbol), key=lambda x: x.name))

    variable = arguments[1][1:]
    if variable:
        variables.remove(variable[0])
        variables.insert(0, variable[0])

    return {
        'function': arguments[1][0],
        'variables': variables,
        'variable': variables[0],
        'input_evaluated': arguments[1][0]
    }

def extract_plot(arguments, evaluated):
    result = {}
    if arguments.args:
        if isinstance(arguments.args[0], sympy.Basic):
            result['variables'] = list(arguments.args[0].atoms(sympy.Symbol))
            result['variable'] = result['variables'][0]
            result['input_evaluated'] = [arguments.args[0]]

            if len(result['variables']) != 1:
                raise ValueError("Cannot plot function of multiple variables")
        else:
            variables = set()
            try:
                for func in arguments.args[0]:
                    variables.update(func.atoms(sympy.Symbol))
            except TypeError:
                raise ValueError("plot() accepts either one function, a list of functions, or keyword arguments")

            variables = list(variables)
            if len(variables) > 1:
                raise ValueError('All functions must have the same and at most one variable')
            if len(variables) == 0:
                variables.append(sympy.Symbol('x'))
            result['variables'] = variables
            result['variable'] = variables[0]
            result['input_evaluated'] = arguments.args[0]
    elif arguments.kwargs:
        result['variables'] = [sympy.Symbol('x')]
        result['variable'] = sympy.Symbol('x')

        parametrics = 1
        functions = {}
        for f in arguments.kwargs:
            if f.startswith('x'):
                y_key = 'y' + f[1:]
                if y_key in arguments.kwargs:
                    # Parametric
                    x = arguments.kwargs[f]
                    y = arguments.kwargs[y_key]
                    functions['p' + str(parametrics)] = (x, y)
                    parametrics += 1
            else:
                if f.startswith('y') and ('x' + f[1:]) in arguments.kwargs:
                    continue
                functions[f] = arguments.kwargs[f]
        result['input_evaluated'] = functions
    return result

# Formatting functions

_function_formatters = {}
def formats_function(name):
    def _formats_function(func):
        _function_formatters[name] = func
        return func
    return _formats_function

@formats_function('diophantine')
def format_diophantine(result, arguments, formatter):
    variables = list(sorted(arguments.args[0].atoms(sympy.Symbol), key=str))
    if isinstance(result, set):
        return format_nested_list_title(*variables)(result, formatter)
    else:
        return format_nested_list_title(*variables)([result], formatter)

def format_by_type(result, arguments=None, formatter=None, function_name=None):
    """
    Format something based on its type and on the input to Gamma.
    """
    if arguments and not function_name:
        function_name = arguments[0]
    if function_name in _function_formatters:
        return _function_formatters[function_name](result, arguments, formatter)
    elif function_name in all_cards and 'format_output_function' in all_cards[function_name].card_info:
        return all_cards[function_name].format_output(result, formatter)
    elif isinstance(result, (list, tuple)):
        return format_list(result, formatter)
    else:
        return formatter(result)

def format_nothing(arg, formatter):
    return arg

def format_steps(arg, formatter):
    return '<div class="steps">{}</div>'.format(arg)

def format_long_integer(line, integer, variable):
    intstr = str(integer)
    if len(intstr) > 100:
        # \xe2 is Unicode ellipsis
        return intstr[:20] + "..." + intstr[len(intstr) - 21:]
    return line % intstr

def format_integral(line, result, components):
    if components['limits']:
        limits = ', '.join(map(repr, components['limits']))
    else:
        limits = ', '.join(map(repr, components['variables']))

    return line.format(_var=limits) % components['integrand']

def format_function_docs_input(line, function, components):
    function = getattr(components['input_evaluated'], '__name__', str(function))
    return line % function

def format_dict_title(*title):
    def _format_dict(dictionary, formatter):
        html = ['<table>',
                '<thead><tr><th>{}</th><th>{}</th></tr></thead>'.format(*title),
                '<tbody>']
        try:
            fdict = dictionary.iteritems()
            if not any(isinstance(i,Symbol) for i in dictionary.keys()):
                fdict = sorted(dictionary.iteritems())
            for key, val in fdict:
                html.append('<tr><td>{}</td><td>{}</td></tr>'.format(key, val))
        except AttributeError, TypeError:  # not iterable/not a dict
            return formatter(dictionary)
        html.append('</tbody></table>')
        return '\n'.join(html)
    return _format_dict

def format_list(items, formatter):
    try:
        if len(items) == 0:
            return "<p>No result</p>"
        html = ['<ul>']
        for item in items:
            html.append('<li>{}</li>'.format(formatter(item)))
        html.append('</ul>')
        return '\n'.join(html)
    except TypeError:  # not iterable, like None
        return formatter(items)

def format_nested_list_title(*titles):
    def _format_nested_list_title(items, formatter):
        try:
            if len(items) == 0:
                return "<p>No result</p>"
            html = ['<table>', '<thead><tr>']
            for title in titles:
                html.append('<th>{}</th>'.format(title))
            html.append('</tr></thead>')
            html.append('<tbody>')
            for item in items:
                html.append('<tr>')
                for subitem in item:
                    html.append('<td>{}</td>'.format(formatter(subitem)))
                html.append('</tr>')
            html.append('</tbody></table>')
            return '\n'.join(html)
        except TypeError:  # not iterable, like None
            return formatter(items)
    return _format_nested_list_title

def format_series_fake_title(title, evaluated):
    if len(evaluated.args) >= 3:
        about = evaluated.args[2]
    else:
        about = 0
    if len(evaluated.args) >= 4:
        up_to = evaluated.args[3]
    else:
        up_to = 6
    return title.format(about, up_to)

def format_truth_table(table, formatter):
    # table is (variables, [(bool, bool...)] representing combination of values
    # and result
    variables, table = table
    titles = list(map(str, variables))
    titles.append("Value")
    def formatter(x):
        if x is True:
            return '<span class="true">True</span>'
        elif x is False:
            return '<span class="false">False</span>'
        else:
            return str(x)
    return format_nested_list_title(*titles)(table, formatter)

def format_approximator(approximation, formatter):
    obj, digits = approximation
    return formatter(obj, r'\approx', obj.evalf(digits))

DIAGRAM_CODE = """
<div class="factorization-diagram" data-primes="{primes}">
    <div></div>
    <p><a href="http://mathlesstraveled.com/2012/10/05/factorization-diagrams/">About this diagram</a></p>
</div>
"""

def format_factorization_diagram(factors, formatter):
    primes = []
    for prime in reversed(sorted(factors)):
        times = factors[prime]
        primes.extend([prime] * times)
    return DIAGRAM_CODE.format(primes=primes)

PLOTTING_CODE = """
<div class="plot"
     data-variable="{variable}">
<div class="graphs">{graphs}</div>
</div>
"""

def format_plot(plot_data, formatter):
    return PLOTTING_CODE.format(**plot_data)

def format_plot_input(result_statement, input_repr, components):
    if 'input_evaluated' in components:
        functions = components['input_evaluated']
        if isinstance(functions, list):
            functions = ['<span>{}</span>'.format(f) for f in functions]
            if len(functions) > 1:
                return 'plot([{}])'.format(', '.join(functions))
            else:
                return 'plot({})'.format(functions[0])
        elif isinstance(functions, dict):
            return 'plot({})'.format(', '.join(
                '<span>{}={}</span>'.format(y, x)
                for y, x in functions.items()))
    else:
        return 'plot({})'.format(input_repr)

GRAPH_TYPES = {
    'xy': [lambda x, y: x, lambda x, y: y],
    'parametric': [lambda x, y: x, lambda x, y: y],
    'polar': [lambda x, y: float(y * sympy.cos(x)),
              lambda x, y: float(y * sympy.sin(x))]
}

def determine_graph_type(key):
    if key.startswith('r'):
        return 'polar'
    elif key.startswith('p'):
        return 'parametric'
    else:
        return 'xy'

def eval_plot(evaluator, components, parameters=None):
    if parameters is None:
        parameters = {}

    xmin, xmax = parameters.get('xmin', -10), parameters.get('xmax', 10)
    pmin, pmax = parameters.get('tmin', 0), parameters.get('tmax', 2 * sympy.pi)
    tmin, tmax = parameters.get('tmin', 0), parameters.get('tmax', 10)
    from sympy.plotting.plot import LineOver1DRangeSeries, Parametric2DLineSeries
    functions = evaluator.get("input_evaluated")
    if isinstance(functions, sympy.Basic):
        functions = [(functions, 'xy')]
    elif isinstance(functions, list):
        functions = [(f, 'xy') for f in functions]
    elif isinstance(functions, dict):
        functions = [(f, determine_graph_type(key)) for key, f in functions.items()]

    graphs = []
    for func, graph_type in functions:
        if graph_type == 'parametric':
            x_func, y_func = func
            x_vars, y_vars = x_func.free_symbols, y_func.free_symbols
            variables = x_vars.union(y_vars)
            if x_vars != y_vars:
                raise ValueError("Both functions in a parametric plot must have the same variable")
        else:
            variables = func.free_symbols

        if len(variables) > 1:
            raise ValueError("Cannot plot multivariate function")
        elif len(variables) == 0:
            variable = sympy.Symbol('x')
        else:
            variable = list(variables)[0]

        try:
            if graph_type == 'xy':
                graph_range = (variable, xmin, xmax)
            elif graph_type == 'polar':
                graph_range = (variable, pmin, pmax)
            elif graph_type == 'parametric':
                graph_range = (variable, tmin, tmax)

            if graph_type in ('xy', 'polar'):
                series = LineOver1DRangeSeries(func, graph_range, nb_of_points=150)
            elif graph_type == 'parametric':
                series = Parametric2DLineSeries(x_func, y_func, graph_range, nb_of_points=150)
            # returns a list of [[x,y], [next_x, next_y]] pairs
            series = series.get_segments()
        except TypeError:
            raise ValueError("Cannot plot function")

        xvalues = []
        yvalues = []

        def limit_y(y):
            CEILING = 1e8
            if y > CEILING:
                y = CEILING
            if y < -CEILING:
                y = -CEILING
            return y

        x_transform, y_transform = GRAPH_TYPES[graph_type]
        series.append([series[-1][1], None])
        for point in series:
            if point[0][1] is None:
                continue
            x = point[0][0]
            y = limit_y(point[0][1])
            xvalues.append(x_transform(x, y))
            yvalues.append(y_transform(x, y))

        graphs.append({
            'type': graph_type,
            'function': sympy.jscode(sympy.sympify(func)),
            'points': {
                'x': xvalues,
                'y': yvalues
            },
            'data': None
        })
    return {
        'variable': repr(variable),
        'graphs': json.dumps(graphs)
    }

def eval_factorization(evaluator, components, parameters=None):
    number = evaluator.get("input_evaluated")

    if number == 0:
        raise ValueError("Can't factor 0")

    factors = sympy.ntheory.factorint(number, limit=100)
    smallfactors = {}
    for factor in factors:
        if factor <= 100:
            smallfactors[factor] = factors[factor]
    return smallfactors

def eval_factorization_diagram(evaluator, components, parameters=None):
    # Raises ValueError (stops card from appearing) if the factors are too
    # large so that the diagram will look nice
    number = int(evaluator.eval("input_evaluated"))
    if number > 256:
        raise ValueError("Number too large")
    elif number == 0:
        raise ValueError("Can't factor 0")
    factors = sympy.ntheory.factorint(number, limit=101)
    smallfactors = {}
    for factor in factors:
        if factor <= 256:
            smallfactors[factor] = factors[factor]
        else:
            raise ValueError("Number too large")
    return smallfactors

def eval_integral(evaluator, components, parameters=None):
    return sympy.integrate(components['integrand'], *components['limits'])

def eval_integral_manual(evaluator, components, parameters=None):
    return sympy.integrals.manualintegrate(components['integrand'],
                                           components['variable'])

def eval_diffsteps(evaluator, components, parameters=None):
    function = components.get('function', evaluator.get('input_evaluated'))

    return diffsteps.print_html_steps(function,
                                      components['variable'])

def eval_intsteps(evaluator, components, parameters=None):
    integrand = components.get('integrand', evaluator.get('input_evaluated'))

    return intsteps.print_html_steps(integrand, components['variable'])

# http://www.python.org/dev/peps/pep-0257/
def trim(docstring):
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def eval_function_docs(evaluator, components, parameters=None):
    docstring = trim(evaluator.get("input_evaluated").__doc__)
    return docutils.core.publish_parts(docstring, writer_name='html4css1',
                                       settings_overrides={'_disable_config': True})['html_body']

def eval_truth_table(evaluator, components, parameters=None):
    expr = evaluator.get("input_evaluated")
    variables = list(sorted(expr.atoms(sympy.Symbol), key=str))

    result = []
    for combination in itertools.product([True, False], repeat=len(variables)):
        result.append(combination +(expr.subs(zip(variables, combination)),))
    return variables, result



def eval_approximator(evaluator, components, parameters=None):
    if parameters is None:
        raise ValueError
    digits = parameters.get('digits', 10)
    return (evaluator.get('input_evaluated'), digits)

# Result cards

no_pre_output = lambda *args: ""

all_cards = {
    'roots': ResultCard(
        "Roots",
        "solve(%s, {_var})",
        lambda statement, var, *args: var,
        format_output_function=format_list),

    'integral': ResultCard(
        "Integral",
        "integrate(%s, {_var})",
        sympy.Integral),

    'integral_fake': FakeResultCard(
        "Integral",
        "integrate(%s, {_var})",
        lambda i, var: sympy.Integral(i, *var),
        eval_method=eval_integral,
        format_input_function=format_integral
    ),

    'integral_manual': ResultCard(
        "Integral",
        "sympy.integrals.manualintegrate(%s, {_var})",
        sympy.Integral),

    'integral_manual_fake': FakeResultCard(
        "Integral",
        "sympy.integrals.manualintegrate(%s, {_var})",
        lambda i, var: sympy.Integral(i, *var),
        eval_method=eval_integral_manual,
        format_input_function=format_integral
    ),

    'diff': ResultCard("Derivative",
                       "diff(%s, {_var})",
                       sympy.Derivative),

    'diffsteps': FakeResultCard(
        "Derivative Steps",
        "diff(%s, {_var})",
        no_pre_output,
        format_output_function=format_steps,
        eval_method=eval_diffsteps),

    'intsteps': FakeResultCard(
        "Integral Steps",
        "integrate(%s, {_var})",
        no_pre_output,
        format_output_function=format_steps,
        eval_method=eval_intsteps,
        format_input_function=format_integral),

    'series': ResultCard(
        "Series expansion around 0",
        "series(%s, {_var}, 0, 10)",
        no_pre_output),

    'digits': ResultCard(
        "Digits in base-10 expansion of number",
        "len(str(%s))",
        no_pre_output,
        multivariate=False,
        format_input_function=format_long_integer),

    'factorization': FakeResultCard(
        "Factors less than 100",
        "factorint(%s, limit=100)",
        no_pre_output,
        multivariate=False,
        format_input_function=format_long_integer,
        format_output_function=format_dict_title("Factor", "Times"),
        eval_method=eval_factorization),

    'factorizationDiagram': FakeResultCard(
        "Factorization Diagram",
        "factorint(%s, limit=256)",
        no_pre_output,
        multivariate=False,
        format_output_function=format_factorization_diagram,
        eval_method=eval_factorization_diagram),

    'float_approximation': ResultCard(
        "Floating-point approximation",
        "(%s).evalf({digits})",
        no_pre_output,
        multivariate=False,
        parameters=['digits']),

    'fractional_approximation': ResultCard(
        "Fractional approximation",
        "nsimplify(%s)",
        no_pre_output,
        multivariate=False),

    'absolute_value': ResultCard(
        "Absolute value",
        "Abs(%s)",
        lambda s, *args: sympy.Abs(s, evaluate=False),
        multivariate=False),

    'polar_angle': ResultCard(
        "Angle in the complex plane",
        "atan2(*(%s).as_real_imag()).evalf()",
        lambda s, *args: sympy.atan2(*s.as_real_imag()),
        multivariate=False),

    'conjugate': ResultCard(
        "Complex conjugate",
        "conjugate(%s)",
        lambda s, *args: sympy.conjugate(s),
        multivariate=False),

    'trigexpand': ResultCard(
        "Alternate form",
        "(%s).expand(trig=True)",
        lambda statement, var, *args: statement,
        multivariate=False),

    'trigsimp': ResultCard(
        "Alternate form",
        "trigsimp(%s)",
        lambda statement, var, *args: statement,
        multivariate=False),

    'trigsincos': ResultCard(
        "Alternate form",
        "(%s).rewrite(csc, sin, sec, cos, cot, tan)",
        lambda statement, var, *args: statement,
        multivariate=False
    ),

    'trigexp': ResultCard(
        "Alternate form",
        "(%s).rewrite(sin, exp, cos, exp, tan, exp)",
        lambda statement, var, *args: statement,
        multivariate=False
    ),

    'plot': FakeResultCard(
        "Plot",
        "plot(%s)",
        no_pre_output,
        format_input_function=format_plot_input,
        format_output_function=format_plot,
        eval_method=eval_plot,
        parameters=['xmin', 'xmax', 'tmin', 'tmax', 'pmin', 'pmax']),

    'function_docs': FakeResultCard(
        "Documentation",
        "help(%s)",
        no_pre_output,
        multivariate=False,
        eval_method=eval_function_docs,
        format_input_function=format_function_docs_input,
        format_output_function=format_nothing
    ),

    'root_to_polynomial': ResultCard(
        "Polynomial with this root",
        "minpoly(%s)",
        no_pre_output,
        multivariate=False
    ),

    'matrix_inverse': ResultCard(
        "Inverse of matrix",
        "(%s).inv()",
        lambda statement, var, *args: sympy.Pow(statement, -1, evaluate=False),
        multivariate=False
    ),

    'matrix_eigenvals': ResultCard(
        "Eigenvalues",
        "(%s).eigenvals()",
        no_pre_output,
        multivariate=False,
        format_output_function=format_dict_title("Eigenvalue", "Multiplicity")
    ),

    'matrix_eigenvectors': ResultCard(
        "Eigenvectors",
        "(%s).eigenvects()",
        no_pre_output,
        multivariate=False,
        format_output_function=format_list
    ),

    'satisfiable': ResultCard(
        "Satisfiability",
        "satisfiable(%s)",
        no_pre_output,
        multivariate=False,
        format_output_function=format_dict_title('Variable', 'Possible Value')
    ),

    'truth_table': FakeResultCard(
        "Truth table",
        "%s",
        no_pre_output,
        multivariate=False,
        eval_method=eval_truth_table,
        format_output_function=format_truth_table
    ),

    'doit': ResultCard(
        "Result",
        "(%s).doit()",
        no_pre_output
    ),

    'approximator': FakeResultCard(
        "Approximator_NOT_USER_VISIBLE",
        "%s",
        no_pre_output,
        eval_method=eval_approximator,
        format_output_function=format_approximator
    ),
}

def get_card(name):
    return all_cards.get(name, None)

all_cards['trig_alternate'] = MultiResultCard(
    "Alternate forms",
    get_card('trigexpand'),
    get_card('trigsimp'),
    get_card('trigsincos'),
    get_card('trigexp')
)

all_cards['integral_alternate'] = MultiResultCard(
    "Antiderivative forms",
    get_card('integral'),
    get_card('integral_manual')
)

all_cards['integral_alternate_fake'] = MultiResultCard(
    "Antiderivative forms",
    get_card('integral_fake'),
    get_card('integral_manual_fake')
)

"""
Syntax:

(predicate, extract_components, result_cards)

predicate: str or func
  If a string, names a function that uses this set of result cards.
  If a function, the function, given the evaluated input, returns True if
  this set of result cards should be used.

extract_components: None or func
  If None, use the default function.
  If a function, specifies a function that parses the input expression into
  a components dictionary. For instance, for an integral, this function
  might extract the limits, integrand, and variable.

result_cards: None or list
  If None, do not show any result cards for this function beyond the
  automatically generated 'Result' and 'Simplification' cards (if they are
  applicable).
  If a list, specifies a list of result cards to display.
"""
result_sets = [
    ('integrate', extract_integral, ['integral_alternate_fake', 'intsteps']),
    ('diff', extract_derivative, ['diff', 'diffsteps']),
    ('factorint', extract_first, ['factorization', 'factorizationDiagram']),
    ('help', extract_first, ['function_docs']),
    ('plot', extract_plot, ['plot']),
    ('rsolve', None, None),
    ('product', None, []),  # suppress automatic Result card
    (is_integer, None, ['digits', 'factorization', 'factorizationDiagram']),
    (is_complex, None, ['absolute_value', 'polar_angle', 'conjugate']),
    (is_rational, None, ['float_approximation']),
    (is_float, None, ['fractional_approximation']),
    (is_approximatable_constant, None, ['root_to_polynomial']),
    (is_uncalled_function, None, ['function_docs']),
    (is_trig, None, ['trig_alternate']),
    (is_matrix, None, ['matrix_inverse', 'matrix_eigenvals', 'matrix_eigenvectors']),
    (is_logic, None, ['satisfiable', 'truth_table']),
    (is_sum, None, ['doit']),
    (is_product, None, ['doit']),
    (is_sum, None, None),
    (is_product, None, None),
    (is_not_constant_basic, None, ['plot', 'roots', 'diff', 'integral_alternate', 'series'])
]

learn_more_sets = {
    'rsolve': ['http://en.wikipedia.org/wiki/Recurrence_relation',
               'http://mathworld.wolfram.com/RecurrenceEquation.html',
               'http://docs.sympy.org/latest/modules/solvers/solvers.html#recurrence-equtions']
}

def is_function_handled(function_name):
    """Do any of the result sets handle this specific function?"""
    if function_name == "simplify":
        return True
    return any(name == function_name for (name, _, cards) in result_sets if cards is not None)

def find_result_set(function_name, input_evaluated):
    """
    Finds a set of result cards based on function name and evaluated input.

    Returns:

    - Function that parses the evaluated input into components. For instance,
      for an integral this would extract the integrand and limits of integration.
      This function will always extract the variables.
    - List of result cards.
    """
    result = []
    result_converter = default_variable

    for predicate, converter, result_cards in result_sets:
        if predicate == function_name:
            if converter:
                result_converter = converter
            if result_cards is None:
                return result_converter, result
            for card in result_cards:
                if card not in result:
                    result.append(card)
        elif callable(predicate) and predicate(input_evaluated):
            if converter:
                result_converter = converter
            if result_cards is None:
                return result_converter, result
            for card in result_cards:
                if card not in result:
                    result.append(card)

    return result_converter, result

def find_learn_more_set(function_name):
    urls = learn_more_sets.get(function_name)
    if urls:
        return '<div class="document"><ul>{}</ul></div>'.format('\n'.join('<li><a href="{0}">{0}</a></li>'.format(url) for url in urls))

########NEW FILE########
__FILENAME__ = stepprinter
import sympy
import collections
from contextlib import contextmanager

from sympy import latex

def Rule(name, props=""):
    # GOTCHA: namedtuple class name not considered!
    def __eq__(self, other):
        return self.__class__ == other.__class__ and tuple.__eq__(self, other)
    __neq__ = lambda self, other: not __eq__(self, other)
    cls = collections.namedtuple(name, props + " context symbol")
    cls.__eq__ = __eq__
    cls.__ne__ = __neq__
    return cls

def functionnames(numterms):
    if numterms == 2:
        return ["f", "g"]
    elif numterms == 3:
        return ["f", "g", "h"]
    else:
        return ["f_{}".format(i) for i in range(numterms)]

def replace_u_var(rule, old_u, new_u):
    d = rule._asdict()
    for field, val in d.items():
        if isinstance(val, sympy.Basic):
            d[field] = val.subs(old_u, new_u)
        elif isinstance(val, tuple):
            d[field] = replace_u_var(val, old_u, new_u)
        elif isinstance(val, list):
            result = []
            for item in val:
                if isinstance(item, tuple):
                    result.append(replace_u_var(item, old_u, new_u))
                else:
                    result.append(item)
            d[field] = result
    return rule.__class__(**d)

# def replace_all_u_vars(rule, replacements=None):
#     if replacements is None:
#         replacements = []

#     d = rule._asdict()
#     for field, val in d.items():
#         if isinstance(val, sympy.Basic):
#             for dummy in val.find(sympy.Dummy):
#                 replacements.append((dummy, ))
#         elif isinstance(val, tuple):
#             pass
#     return rule.__class__(**d)

class Printer(object):
    def __init__(self):
        self.lines = []
        self.level = 0

    def append(self, text):
        self.lines.append(self.level * "\t" + text)

    def finalize(self):
        return "\n".join(self.lines)

    def format_math(self, math):
        return str(math)

    def format_math_display(self, math):
        return self.format_math(math)

    @contextmanager
    def new_level(self):
        self.level += 1
        yield self.level
        self.level -= 1

    @contextmanager
    def new_step(self):
        yield self.level
        self.lines.append('\n')

class LaTeXPrinter(Printer):
    def format_math(self, math):
        return latex(math)

class HTMLPrinter(LaTeXPrinter):
    def __init__(self):
        super(HTMLPrinter, self).__init__()
        self.lines = ['<ol>']

    def format_math(self, math):
        return '<script type="math/tex; mode=inline">{}</script>'.format(
            latex(math))

    def format_math_display(self, math):
        if not isinstance(math, basestring):
            math = latex(math)
        return '<script type="math/tex; mode=display">{}</script>'.format(
            math)

    @contextmanager
    def new_level(self):
        self.level += 1
        self.lines.append(' ' * 4 * self.level + '<ol>')
        yield
        self.lines.append(' ' * 4 * self.level + '</ol>')
        self.level -= 1

    @contextmanager
    def new_step(self):
        self.lines.append(' ' * 4 * self.level + '<li>')
        yield self.level
        self.lines.append(' ' * 4 * self.level + '</li>')

    @contextmanager
    def new_collapsible(self):
        self.lines.append(' ' * 4 * self.level + '<div class="collapsible">')
        yield self.level
        self.lines.append(' ' * 4 * self.level + '</div>')

    @contextmanager
    def new_u_vars(self):
        self.u, self.du = sympy.Symbol('u'), sympy.Symbol('du')
        yield self.u, self.du

    def append(self, text):
        self.lines.append(' ' * 4 * (self.level + 1) + '<p>{}</p>'.format(text))

    def append_header(self, text):
        self.lines.append(' ' * 4 * (self.level + 1) + '<h2>{}</h2>'.format(text))

########NEW FILE########
__FILENAME__ = utils
from __future__ import division
import difflib
import collections
import traceback
import sys
import ast
import re
from StringIO import StringIO
import sympy

from sympy.core.relational import Relational
import sympy.parsing.sympy_tokenize as sympy_tokenize
from token import NAME

OTHER_SYMPY_FUNCTIONS = ('sqrt',)

Arguments = collections.namedtuple('Arguments', 'function args kwargs')

class Eval(object):
    def __init__(self, namespace={}):
        self._namespace = namespace

    def get(self, name):
        return self._namespace.get(name)

    def set(self, name, value):
        self._namespace[name] = value

    def eval_node(self, node):
        tree = ast.fix_missing_locations(ast.Expression(node))
        return eval(compile(tree, '<string>', 'eval'), self._namespace)

    def eval(self, x, use_none_for_exceptions=False, repr_expression=True):
        globals = self._namespace
        try:
            x = x.strip()
            x = x.replace("\r", "")
            y = x.split('\n')
            if len(y) == 0:
                return ''
            s = '\n'.join(y[:-1]) + '\n'
            t = y[-1]
            try:
                z = compile(t + '\n', '', 'eval')
            except SyntaxError:
                s += '\n' + t
                z = None

            try:
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                eval(compile(s, '', 'exec', division.compiler_flag), globals, globals)

                if not z is None:
                    r = eval(z, globals)

                    if repr_expression:
                        r = repr(r)
                else:
                    r = ''

                if repr_expression:
                    sys.stdout.seek(0)
                    r = sys.stdout.read() + r
            finally:
                sys.stdout = old_stdout
            return r
        except:
            if use_none_for_exceptions:
                return
            etype, value, tb = sys.exc_info()
            # If we decide in the future to remove the first frame fromt he
            # traceback (since it links to our code, so it could be confusing
            # to the user), it's easy to do:
            #tb = tb.tb_next
            s = "".join(traceback.format_exception(etype, value, tb))
            return s

class LatexVisitor(ast.NodeVisitor):
    EXCEPTIONS = {'integrate': sympy.Integral, 'diff': sympy.Derivative}
    formatters = {}

    @staticmethod
    def formats_function(name):
        def _formats_function(f):
            LatexVisitor.formatters[name] = f
            return f
        return _formats_function

    def format(self, name, node):
        formatter = LatexVisitor.formatters.get(name)

        if not formatter:
            return None

        return formatter(node, self)

    def visit_Call(self, node):
        buffer = []
        fname = node.func.id

        # Only apply to lowercase names (i.e. functions, not classes)
        if fname in self.__class__.EXCEPTIONS:
            node.func.id = self.__class__.EXCEPTIONS[fname].__name__
            self.latex = sympy.latex(self.evaluator.eval_node(node))
        else:
            result = self.format(fname, node)
            if result:
                self.latex = result
            elif fname[0].islower() and fname not in OTHER_SYMPY_FUNCTIONS:
                buffer.append("\\mathrm{%s}" % fname.replace('_', '\\_'))
                buffer.append('(')

                latexes = []
                for arg in node.args:
                    if isinstance(arg, ast.Call) and getattr(arg.func, 'id', None) and arg.func.id[0].lower() == arg.func.id[0]:
                        latexes.append(self.visit_Call(arg))
                    else:
                        latexes.append(sympy.latex(self.evaluator.eval_node(arg)))

                buffer.append(', '.join(latexes))
                buffer.append(')')

                self.latex = ''.join(buffer)
            else:
                self.latex = sympy.latex(self.evaluator.eval_node(node))
        return self.latex

@LatexVisitor.formats_function('solve')
def format_solve(node, visitor):
    expr = visitor.evaluator.eval_node(node.args[0])
    buffer = [r'\mathrm{solve}\;', sympy.latex(expr)]

    if not isinstance(expr, Relational):
        buffer.append('=0')

    if len(node.args) > 1:
        buffer.append(r'\;\mathrm{for}\;')
    for arg in node.args[1:]:
        buffer.append(sympy.latex(visitor.evaluator.eval_node(arg)))
        buffer.append(r',\, ')
    if len(node.args) > 1:
        buffer.pop()

    return ''.join(buffer)

@LatexVisitor.formats_function('limit')
def format_limit(node, visitor):
    if len(node.args) >= 3:
        return sympy.latex(
            sympy.Limit(*[visitor.evaluator.eval_node(arg) for arg in node.args]))

@LatexVisitor.formats_function('prime')
def format_prime(node, visitor):
    number = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    return ''.join([number,
                    r'^\mathrm{',
                    ordinal(int(number)),
                    r'}\; \mathrm{prime~number}'])

@LatexVisitor.formats_function('isprime')
def format_isprime(node, visitor):
    number = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    return ''.join([r'\mathrm{Is~}', number, r'\mathrm{~prime?}'])

@LatexVisitor.formats_function('nextprime')
def format_nextprime(node, visitor):
    number = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    return r'\mathrm{Least~prime~greater~than~}' + number

@LatexVisitor.formats_function('factorint')
def format_factorint(node, visitor):
    number = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    return r'\mathrm{Prime~factorization~of~}' + number

@LatexVisitor.formats_function('factor')
def format_factor(node, visitor):
    expression = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    return r'\mathrm{Factorization~of~}' + expression

@LatexVisitor.formats_function('solve_poly_system')
def format_factorint(node, visitor):
    equations = visitor.evaluator.eval_node(node.args[0])
    variables = tuple(map(visitor.evaluator.eval_node, node.args[1:]))

    if len(variables) == 1:
        variables = variables[0]

    return ''.join([r'\mathrm{Solve~} \begin{cases} ',
                    r'\\'.join(map(sympy.latex, equations)),
                    r'\end{cases} \mathrm{~for~}',
                    sympy.latex(variables)])

@LatexVisitor.formats_function('plot')
def format_plot(node, visitor):
    if node.args:
        function = sympy.latex(visitor.evaluator.eval_node(node.args[0]))
    else:
        keywords = {}
        for keyword in node.keywords:
            keywords[keyword.arg] = visitor.evaluator.eval_node(keyword.value)
        function = sympy.latex(keywords)
    return r'\mathrm{Plot~}' + function

@LatexVisitor.formats_function('rsolve')
def format_rsolve(node, visitor):
    recurrence = sympy.latex(sympy.Eq(visitor.evaluator.eval_node(node.args[0]), 0))
    if len(node.args) == 3:
        conds = visitor.evaluator.eval_node(node.args[2])
        initconds = '\\\\\n'.join('&' + sympy.latex(sympy.Eq(eqn, val)) for eqn, val in conds.items())
        text = r'&\mathrm{Solve~the~recurrence~}' + recurrence + r'\\'
        condstext = r'&\mathrm{with~initial~conditions}\\'
        return r'\begin{align}' + text + condstext + initconds + r'\end{align}'
    else:
        return r'\mathrm{Solve~the~recurrence~}' + recurrence

diophantine_template = (r"\begin{{align}}&{}\\&\mathrm{{where~}}"
                        r"{}\mathrm{{~are~integers}}\end{{align}}")
@LatexVisitor.formats_function('diophantine')
def format_diophantine(node, visitor):
    expression = visitor.evaluator.eval_node(node.args[0])
    symbols = None
    if isinstance(expression, sympy.Basic):
        symbols = expression.free_symbols
    equation = sympy.latex(sympy.Eq(expression, 0))

    result = r'\mathrm{Solve~the~diophantine~equation~}' + equation
    if symbols:
        result = diophantine_template.format(result, tuple(symbols))
    return result

@LatexVisitor.formats_function('summation')
@LatexVisitor.formats_function('product')
def format_diophantine(node, visitor):
    if node.func.id == 'summation':
        klass = sympy.Sum
    else:
        klass = sympy.Product
    return sympy.latex(klass(*map(visitor.evaluator.eval_node, node.args)))

@LatexVisitor.formats_function('help')
def format_help(node, visitor):
    if node.args:
        function = visitor.evaluator.eval_node(node.args[0])
        return r'\mathrm{Show~documentation~for~}' + function.__name__
    return r'\mathrm{Show~documentation~(requires~1~argument)}'

class TopCallVisitor(ast.NodeVisitor):
    def __init__(self):
        super(TopCallVisitor, self).__init__()
        self.call = None

    def visit_Call(self, node):
        self.call = node

    def visit_Name(self, node):
        if not self.call:
            self.call = node

# From http://stackoverflow.com/a/739301/262727
def ordinal(n):
    if 10 <= n % 100 < 20:
        return 'th'
    else:
       return {1 : 'st', 2 : 'nd', 3 : 'rd'}.get(n % 10, "th")

# TODO: modularize all of this
def latexify(string, evaluator):
    a = LatexVisitor()
    a.evaluator = evaluator
    a.visit(ast.parse(string))
    return a.latex

def topcall(string):
    a = TopCallVisitor()
    a.visit(ast.parse(string))
    if hasattr(a, 'call'):
        return getattr(a.call.func, 'id', None)
    return None

def arguments(string_or_node, evaluator):
    node = None
    if not isinstance(string_or_node, ast.Call):
        a = TopCallVisitor()
        a.visit(ast.parse(string_or_node))

        if hasattr(a, 'call'):
            node = a.call
    else:
        node = string_or_node

    if node:
        if isinstance(node, ast.Call):
            name = getattr(node.func, 'id', None)  # when is it undefined?
            args, kwargs = None, None
            if node.args:
                args = list(map(evaluator.eval_node, node.args))

            kwargs = node.keywords
            if kwargs:
                kwargs = {kwarg.arg: evaluator.eval_node(kwarg.value) for kwarg in kwargs}

            return Arguments(name, args, kwargs)
        elif isinstance(node, ast.Name):
            return Arguments(node.id, [], {})
    return None

re_calls = re.compile(r'(Integer|Symbol|Float|Rational)\s*\([\'\"]?([a-zA-Z0-9\.]+)[\'\"]?\s*\)')

def re_calls_sub(match):
    return match.groups()[1]

def removeSymPy(string):
    try:
        return re_calls.sub(re_calls_sub, string)
    except IndexError:
        return string

from sympy.parsing.sympy_parser import (
    AppliedFunction, implicit_multiplication, split_symbols,
    function_exponentiation, implicit_application, OP, NAME,
    _group_parentheses, _apply_functions, _flatten, _token_callable)

def _implicit_multiplication(tokens, local_dict, global_dict):
    result = []

    for tok, nextTok in zip(tokens, tokens[1:]):
        result.append(tok)
        if (isinstance(tok, AppliedFunction) and
              isinstance(nextTok, AppliedFunction)):
            result.append((OP, '*'))
        elif (isinstance(tok, AppliedFunction) and
              nextTok[0] == OP and nextTok[1] == '('):
            # Applied function followed by an open parenthesis
            if (tok.function[1] == 'Symbol' and
                len(tok.args[1][1]) == 3):
                # Allow implicit function symbol creation
                # TODO XXX need some way to offer alternative parsing here -
                # sometimes we want this and sometimes not, hard to tell when
                # (making it context-sensitive based on input function best)
                continue
            result.append((OP, '*'))
        elif (tok[0] == OP and tok[1] == ')' and
              isinstance(nextTok, AppliedFunction)):
            # Close parenthesis followed by an applied function
            result.append((OP, '*'))
        elif (tok[0] == OP and tok[1] == ')' and
              nextTok[0] == NAME):
            # Close parenthesis followed by an implicitly applied function
            result.append((OP, '*'))
        elif (tok[0] == nextTok[0] == OP
              and tok[1] == ')' and nextTok[1] == '('):
            # Close parenthesis followed by an open parenthesis
            result.append((OP, '*'))
        elif (isinstance(tok, AppliedFunction) and nextTok[0] == NAME):
            # Applied function followed by implicitly applied function
            result.append((OP, '*'))
        elif (tok[0] == NAME and
              not _token_callable(tok, local_dict, global_dict) and
              nextTok[0] == OP and nextTok[1] == '('):
            # Constant followed by parenthesis
            result.append((OP, '*'))
        elif (tok[0] == NAME and
              not _token_callable(tok, local_dict, global_dict) and
              nextTok[0] == NAME and
              not _token_callable(nextTok, local_dict, global_dict)):
            # Constant followed by constant
            result.append((OP, '*'))
        elif (tok[0] == NAME and
              not _token_callable(tok, local_dict, global_dict) and
              (isinstance(nextTok, AppliedFunction) or nextTok[0] == NAME)):
            # Constant followed by (implicitly applied) function
            result.append((OP, '*'))
    if tokens:
        result.append(tokens[-1])
    return result

def implicit_multiplication(result, local_dict, global_dict):
    """Makes the multiplication operator optional in most cases.

    Use this before :func:`implicit_application`, otherwise expressions like
    ``sin 2x`` will be parsed as ``x * sin(2)`` rather than ``sin(2*x)``.

    Example:

    >>> from sympy.parsing.sympy_parser import (parse_expr,
    ... standard_transformations, implicit_multiplication)
    >>> transformations = standard_transformations + (implicit_multiplication,)
    >>> parse_expr('3 x y', transformations=transformations)
    3*x*y
    """
    for step in (_group_parentheses(implicit_multiplication),
                 _apply_functions,
                 _implicit_multiplication):
        result = step(result, local_dict, global_dict)

    result = _flatten(result)
    return result

def custom_implicit_transformation(result, local_dict, global_dict):
    """Allows a slightly relaxed syntax.

    - Parentheses for single-argument method calls are optional.

    - Multiplication is implicit.

    - Symbol names can be split (i.e. spaces are not needed between
      symbols).

    - Functions can be exponentiated.

    Example:

    >>> from sympy.parsing.sympy_parser import (parse_expr,
    ... standard_transformations, implicit_multiplication_application)
    >>> parse_expr("10sin**2 x**2 + 3xyz + tan theta",
    ... transformations=(standard_transformations +
    ... (implicit_multiplication_application,)))
    3*x*y*z + 10*sin(x**2)**2 + tan(theta)

    """
    for step in (split_symbols, implicit_multiplication,
                 implicit_application, function_exponentiation):
        result = step(result, local_dict, global_dict)

    return result


SYNONYMS = {
    u'derivative': 'diff',
    u'derive': 'diff',
    u'integral': 'integrate',
    u'antiderivative': 'integrate',
    u'factorize': 'factor',
    u'graph': 'plot',
    u'draw': 'plot'
}

def synonyms(tokens, local_dict, global_dict):
    """Make some names synonyms for others.

    This is done at the token level so that the "stringified" output that
    Gamma displays shows the correct function name. Must be applied before
    auto_symbol.
    """

    result = []
    for token in tokens:
        if token[0] == NAME:
            if token[1] in SYNONYMS:
                result.append((NAME, SYNONYMS[token[1]]))
                continue
        result.append(token)
    return result

def close_matches(s, global_dict):
    """
    Checks undefined names to see if they are close matches to a defined name.
    """

    tokens = sympy_tokenize.generate_tokens(StringIO(s.strip()).readline)
    result = []
    has_result = False
    all_names = set(global_dict).union(SYNONYMS)

    # strip the token location info to avoid strange untokenize results
    tokens = [(tok[0], tok[1]) for tok in tokens]
    for token in tokens:
        if (token[0] == NAME and
            token[1] not in all_names and
            len(token[1]) > 1):
            matches = difflib.get_close_matches(token[1], all_names)

            if matches and matches[0] == token[1]:
                matches = matches[1:]
            if matches:
                result.append((NAME, matches[0]))
                has_result = True
                continue
        result.append(token)
    if has_result:
        return sympy_tokenize.untokenize(result).strip()
    return None

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import ndb

class Query(ndb.Model):
    text = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    user_id = ndb.StringProperty()

########NEW FILE########
__FILENAME__ = settings
../settings.py
########NEW FILE########
__FILENAME__ = extra_tags
from django import template
import urllib
register = template.Library()

@register.inclusion_tag('card.html')
def show_card(cell, input):
    return {'cell': cell, 'input': input}

@register.tag(name='make_query')
def do_make_query(parser, token):
    try:
        tag_name, query = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a single argument" % token.contents.split()[0])

    return QueryNode(query)

class QueryNode(template.Node):
    def __init__(self, query):
        if query[0] == query[-1] and query[0] in ('"', "'"):
            self.query = query
        else:
            self.query = template.Variable(query)

    def render(self, context):
        if isinstance(self.query, unicode):
            return "/input/?i=" + urllib.quote(self.query[1:-1])
        else:
            return "/input/?i=" + urllib.quote(self.query.resolve(context))

@register.tag(name='make_query_link')
def do_make_query(parser, token):
    try:
        tag_name, query = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a single argument" % token.contents.split()[0])

    return QueryLinkNode(query)

class QueryLinkNode(template.Node):
    def __init__(self, query):
        if query[0] == query[-1] and query[0] in ('"', "'"):
            self.query = query
        else:
            self.query = template.Variable(query)

    def render(self, context):
        if isinstance(self.query, unicode) or isinstance(self.query, str):
            q = self.query[1:-1]
        else:
            q = self.query.resolve(context)

        link = '<a href="/input/?i={0}">{1}</a>'.format(urllib.quote(q), q)
        return link

@register.tag(name='make_example')
def do_make_example(parser, token):
    try:
        tag_name, example = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a single argument" % token.contents.split()[0])

    return ExampleLinkNode(example)

class ExampleLinkNode(template.Node):
    def __init__(self, example):
        self.example = template.Variable(example)

    def render(self, context):
        example = self.example.resolve(context)

        if isinstance(example, tuple):
            title, example = example[0], example[1]
        else:
            title, example = None, example

        buf = []

        if title:
            buf.append('<span>{}</span>'.format(title))

        buf.append('<a href="/input/?i={0}">{1}</a>'.format(
            urllib.quote(example), example))
        return ' '.join(buf)

########NEW FILE########
__FILENAME__ = test_utils
from utils import Eval

def test_eval1():
    e = Eval()
    assert e.eval("1+1") == "2"
    assert e.eval("1+1\n") == "2"
    assert e.eval("a=1+1") == ""
    assert e.eval("a=1+1\n") == ""
    assert e.eval("a=1+1\na") == "2"
    assert e.eval("a=1+1\na\n") == "2"
    assert e.eval("a=1+1\na=3") == ""
    assert e.eval("a=1+1\na=3\n") == ""

def test_eval2():
    e = Eval()
    assert e.eval("""\
def f(x):
    return x**2
f(3)
"""\
        ) == "9"
    assert e.eval("""\
def f(x):
    return x**2
f(3)
a = 5
"""\
        ) == ""
    assert e.eval("""\
def f(x):
    return x**2
if f(3) == 9:
    a = 1
else:
    a = 0
a
"""\
        ) == "1"
    assert e.eval("""\
def f(x):
    return x**2 + 1
if f(3) == 9:
    a = 1
else:
    a = 0
a
"""\
        ) == "0"

def test_eval3():
    e = Eval()
    assert e.eval("xxxx").startswith("Traceback")
    assert e.eval("""\
def f(x):
    return x**2 + 1 + y
if f(3) == 9:
    a = 1
else:
    a = 0
a
"""\
        ).startswith("Traceback")

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template.loader import render_to_string
from django.utils import simplejson
from django import forms
import django

from google.appengine.api import users
from google.appengine.runtime import DeadlineExceededError

import sympy
from logic import Eval, SymPyGamma
from logic.logic import mathjax_latex
from logic.resultsets import get_card, find_result_set

import settings
import models

import os
import random
import json
import urllib
import urllib2
import datetime
import traceback

LIVE_URL = '<a href="http://live.sympy.org">SymPy Live</a>'
LIVE_PROMOTION_MESSAGES = [
    'Need more control? Try ' + LIVE_URL + '.',
    'Want a full Python shell? Use ' + LIVE_URL + '.',
    'Experiment with SymPy at ' + LIVE_URL + '.',
    'Want to compute something more complicated?' +
    ' Try a full Python/SymPy console at ' + LIVE_URL + '.'
]

EXAMPLES = [
    ('Arithmetic', [
        ['Fractions', [('Simplify fractions', '242/33'),
                       ('Rationalize repeating decimals', '0.[123]')]],
        ['Approximations', ['pi', 'E', 'exp(pi)']],
    ]),
    ('Algebra', [
        [None, ['x', '(x+2)/((x+3)(x-4))', 'simplify((x**2 - 4)/((x+3)(x-2)))']],
        ['Polynomial and Rational Functions', [
            ('Polynomial division', 'div(x**2 - 4 + x, x-2)'),
            ('Greatest common divisor', 'gcd(2*x**2 + 6*x, 12*x)'),
            ('&hellip;and least common multiple', 'lcm(2*x**2 + 6*x, 12*x)'),
            ('Factorization', 'factor(x**4/2 + 5*x**3/12 - x**2/3)'),
            ('Multivariate factorization', 'factor(x**2 + 4*x*y + 4*y**2)'),
            ('Symbolic roots', 'solve(x**2 + 4*x*y + 4*y**2)'),
            'solve(x**2 + 4*x*y + 4*y**2, y)',
            ('Complex roots', 'solve(x**2 + 4*x + 181, x)'),
            ('Irrational roots', 'solve(x**3 + 4*x + 181, x)'),
            ('Systems of equations', 'solve_poly_system([y**2 - x**3 + 1, y*x], x, y)'),
        ]],
    ]),
    ('Trigonometry', [
        [None, ['sin(2x)', 'tan(1 + x)']],
    ]),
    ('Calculus', [
        ['Limits', ['limit(tan(x), x, pi/2)', 'limit(tan(x), x, pi/2, dir="-")']],
        ['Derivatives', [
            ('Derive the product rule', 'diff(f(x)*g(x)*h(x))'),
            ('&hellip;as well as the quotient rule', 'diff(f(x)/g(x))'),
            ('Get steps for derivatives', 'diff((sin(x) * x^2) / (1 + tan(cot(x))))'),
            ('Multiple ways to derive functions', 'diff(cot(xy), y)'),
            ('Implicit derivatives, too', 'diff(y(x)^2 - 5sin(x), x)'),
        ]],
        ['Integrals', [
            'integrate(tan(x))',
            ('Multiple variables', 'integrate(2*x + y, y)'),
            ('Limits of integration', 'integrate(2*x + y, (x, 1, 3))'),
            'integrate(2*x + y, (x, 1, 3), (y, 2, 4))',
            ('Improper integrals', 'integrate(tan(x), (x, 0, pi/2))'),
            ('Exact answers', 'integrate(1/(x**2 + 1), (x, 0, oo))'),
            ('Get steps for integrals', 'integrate(exp(x) / (1 + exp(2x)))'),
            'integrate(1 /((x+1)(x+3)(x+5)))',
            'integrate((2x+3)**7)'
        ]],
        ['Series', [
            'series(sin(x), x, pi/2)',
        ]],
    ]),
    ('Number Theory', [
        [None, [
            '1006!',
            'factorint(12321)',
            ('Calculate the 42<sup>nd</sup> prime', 'prime(42)'),
            (r'Calculate \( \varphi(x) \), the Euler totient function', 'totient(42)'),
            'isprime(12321)',
            ('First prime greater than 42', 'nextprime(42)'),
        ]],
        ['Diophantine Equations', [
            'diophantine(x**2 - 4*x*y + 8*y**2 - 3*x + 7*y - 5)',
            'diophantine(2*x + 3*y - 5)',
            'diophantine(3*x**2 + 4*y**2 - 5*z**2 + 4*x*y - 7*y*z + 7*z*x)'
        ]]
    ]),
    ('Discrete Mathematics', [
        ['Boolean Logic', [
            '(x | y) & (x | ~y) & (~x | y)',
            'x & ~x'
        ]],
        ['Recurrences', [
            ('Solve a recurrence relation', 'rsolve(y(n+2)-y(n+1)-y(n), y(n))'),
            ('Specify initial conditions', 'rsolve(y(n+2)-y(n+1)-y(n), y(n), {y(0): 0, y(1): 1})')
        ]],
        ['Summation', [
            'Sum(k,(k,1,m))',
            'Sum(x**k,(k,0,oo))',
            'Product(k**2,(k,1,m))',
            'summation(1/2**i, (i, 0, oo))',
            'product(i, (i, 1, k), (k, 1, n))'
        ]]
    ]),
    ('Plotting', [
        [None, ['plot(sin(x) + cos(2x))',
                ('Multiple plots', 'plot([x, x^2, x^3, x^4])'),
                ('Polar plots', 'plot(r=1-sin(theta))'),
                ('Parametric plots', 'plot(x=cos(t), y=sin(t))'),
                ('Multiple plot types', 'plot(y=x,y1=x^2,r=cos(theta),r1=sin(theta))')]],
    ]),
    ('Miscellaneous', [
        [None, [('Documentation for functions', 'factorial2'),
                'sympify',
                'bernoulli']],
    ]),
]

class MobileTextInput(forms.widgets.TextInput):
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        attrs['autocorrect'] = 'off'
        attrs['autocapitalize'] = 'off'
        return super(MobileTextInput, self).render(name, value, attrs)

class SearchForm(forms.Form):
    i = forms.CharField(required=False, widget=MobileTextInput())

def authenticate(view):
    def _wrapper(request, **kwargs):
        user = users.get_current_user()
        result = view(request, user, **kwargs)

        try:
            template, params = result
        except ValueError:
            return result

        if user:
            params['auth_url'] = users.create_logout_url("/")
            params['auth_message'] = "Logout"
        else:
            params['auth_url'] = users.create_login_url("/")
            params['auth_message'] = "Login"
        return template, params
    return _wrapper

def app_version(view):
    def _wrapper(request, **kwargs):
        result = view(request, **kwargs)
        version, deployed = os.environ['CURRENT_VERSION_ID'].split('.')
        deployed = datetime.datetime.fromtimestamp(long(deployed) / pow(2, 28))
        deployed = deployed.strftime("%d/%m/%y %X")

        try:
            template, params = result
            params['app_version'] = version
            params['app_deployed'] = deployed
            return render_to_response(template, params)
        except ValueError:
            return result
    return _wrapper

@app_version
@authenticate
def index(request, user):
    form = SearchForm()

    if user:
        history = models.Query.query(models.Query.user_id==user.user_id())
        history = history.order(-models.Query.date).fetch(10)
    else:
        history = None

    return ("index.html", {
        "form": form,
        "MEDIA_URL": settings.MEDIA_URL,
        "main_active": "selected",
        "history": history,
        "examples": EXAMPLES
        })

@app_version
@authenticate
def input(request, user):
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            input = form.cleaned_data["i"]

            if input.strip().lower() in ('random', 'example', 'random example'):
                return redirect('/random')

            g = SymPyGamma()
            r = g.eval(input)

            if not r:
                r = [{
                    "title": "Input",
                    "input": input,
                    "output": "Can't handle the input."
                }]

            if (user and not models.Query.query(
                    models.Query.text==input,
                    models.Query.user_id==user.user_id()).get()):
                query = models.Query(text=input, user_id=user.user_id())
                query.put()
            elif not models.Query.query(models.Query.text==input).get():
                query = models.Query(text=input, user_id=None)
                query.put()


            # For some reason the |random tag always returns the same result
            return ("result.html", {
                "input": input,
                "result": r,
                "form": form,
                "MEDIA_URL": settings.MEDIA_URL,
                "promote_live": random.choice(LIVE_PROMOTION_MESSAGES)
                })

@app_version
@authenticate
def about(request, user):
    return ("about.html", {
        "MEDIA_URL": settings.MEDIA_URL,
        "about_active": "selected",
        })

def random_example(request):
    examples = []

    for category in EXAMPLES:
        for subcategory in category[1]:
            for example in subcategory[1]:
                if isinstance(example, tuple):
                    examples.append(example[1])
                else:
                    examples.append(example)

    return redirect('input/?i=' + urllib.quote(random.choice(examples)))

def _process_card(request, card_name):
    variable = request.GET.get('variable')
    expression = request.GET.get('expression')
    if not variable or not expression:
        raise Http404

    variable = urllib2.unquote(variable)
    expression = urllib2.unquote(expression)

    g = SymPyGamma()

    parameters = {}
    for key, val in request.GET.items():
        parameters[key] = ''.join(val)

    return g, variable, expression, parameters


def eval_card(request, card_name):
    g, variable, expression, parameters = _process_card(request, card_name)

    try:
        result = g.eval_card(card_name, expression, variable, parameters)
    except ValueError as e:
        return HttpResponse(json.dumps({
            'error': e.message
        }), mimetype="application/json")
    except DeadlineExceededError:
        return HttpResponse(json.dumps({
            'error': 'Computation timed out.'
        }), mimetype="application/json")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(json.dumps({
            'error': ('There was an error in Gamma. For reference'
                      'the last five traceback entries are: ' + trace)
        }), mimetype="application/json")

    return HttpResponse(json.dumps(result), mimetype="application/json")

def get_card_info(request, card_name):
    g, variable, expression, _ = _process_card(request, card_name)

    try:
        result = g.get_card_info(card_name, expression, variable)
    except ValueError as e:
        return HttpResponse(json.dumps({
            'error': e.message
        }), mimetype="application/json")
    except DeadlineExceededError:
        return HttpResponse(json.dumps({
            'error': 'Computation timed out.'
        }), mimetype="application/json")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(json.dumps({
            'error': ('There was an error in Gamma. For reference'
                      'the last five traceback entries are: ' + trace)
        }), mimetype="application/json")

    return HttpResponse(json.dumps(result), mimetype="application/json")

def get_card_full(request, card_name):
    g, variable, expression, parameters = _process_card(request, card_name)

    try:
        card_info = g.get_card_info(card_name, expression, variable)
        result = g.eval_card(card_name, expression, variable, parameters)
        card_info['card'] = card_name
        card_info['cell_output'] = result['output']

        html = render_to_string('card.html', {
            'cell': card_info,
            'input': expression
        })
    except ValueError as e:
        card_info = g.get_card_info(card_name, expression, variable)
        return HttpResponse(render_to_string('card.html', {
            'cell': {
                'title': card_info['title'],
                'input': card_info['input'],
                'card': card_name,
                'variable': variable,
                'error': e.message
            },
            'input': expression
        }), mimetype="text/html")
    except DeadlineExceededError:
        return HttpResponse('Computation timed out.',
                            mimetype="text/html")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(render_to_string('card.html', {
            'cell': {
                'card': card_name,
                'variable': variable,
                'error': trace
            },
            'input': expression
        }), mimetype="text/html")

    response = HttpResponse(html, mimetype="text/html")
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'

    return response

def remove_query(request, qid):
    user = users.get_current_user()

    if user:
        query = models.ndb.Key(urlsafe=qid).get()

        if not models.Query.query(models.Query.text==query.text):
            query.user_id = None
            query.put()
        else:
            query.key.delete()

        response = {
            'result': 'success',
        }
    else:
        response = {
            'result': 'error',
            'message': 'Not logged in or invalid user.'
        }

    return HttpResponse(json.dumps(response), mimetype='application/json')

@app_version
def view_404(request):
    return ("404.html", {})

@app_version
def view_500(request):
    return ("500.html", {})

########NEW FILE########
__FILENAME__ = main
import os, sys

# Force sys.path to have our own directory first, in case we want to import
# from it.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Must set this env var *before* importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = settings
# Django settings for notebook project.

# root_dir points to this directory (that contains settings.py):
import os
root_dir = os.path.dirname(os.path.abspath(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '4v-c#usznhix_^np%w)4yr@dlit*4^47u@uph3xr2gh@7(&z$u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'google.appengine.ext.ndb.django_middleware.NdbDjangoMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    root_dir + "/templates",
)

INSTALLED_APPS = (
        #'django.contrib.auth',
    'django.contrib.contenttypes',
    'app'
    #'django.contrib.sessions',
    #'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

import os.path
p = os.path.join(os.path.dirname(__file__), 'media/')

urlpatterns = patterns(
    '',
    # Example:
    # (r'^notebook/', include('notebook.foo.urls')),
    (r'^$', 'app.views.index'),

    (r'^input/', 'app.views.input'),
    (r'^about/$', 'app.views.about'),
    (r'^random', 'app.views.random_example'),

    (r'user/remove/(?P<qid>.*)$', 'app.views.remove_query'),

    (r'card/(?P<card_name>\w*)$', 'app.views.eval_card'),

    (r'card_info/(?P<card_name>\w*)$', 'app.views.get_card_info'),

    (r'card_full/(?P<card_name>\w*)$', 'app.views.get_card_full')


    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
)

handler404 = 'app.views.view_404'
handler500 = 'app.views.view_500'

########NEW FILE########
