module main

import strconv

enum TokenKind {
	eof
	newline
	indent
	dedent
	ident
	int_lit
	string_lit
	kw_match
	kw_import
	kw_if
	kw_else
	kw_elif
	kw_pass
	kw_for
	kw_in
	kw_while
	kw_break
	kw_continue
	kw_return
	kw_def
	kw_class
	kw_and
	kw_or
	kw_not
	underscore
	lparen
	rparen
	lbrace
	rbrace
	lbracket
	rbracket
	plus
	minus
	star
	slash
	assign
	comma
	dot
	colon
	lt
	gt
	le
	ge
	eqeq
	noteq
}

struct Token {
	kind TokenKind
	text string
}

type Expr = AttributeExpr | BinaryExpr | BoolOpExpr | CallExpr | CompareExpr | IntExpr | MatchExpr | NameExpr | StringExpr | SubscriptExpr | UnaryExpr

type Pattern = BindPattern | ValuePattern | WildcardPattern

type Stmt = AssignStmt | BreakStmt | ClassDefStmt | ContinueStmt | ExprStmt | ForStmt | FunctionDefStmt | IfStmt | ImportStmt | PassStmt | ReturnStmt | WhileStmt

struct IntExpr {
	value int
}

struct StringExpr {
	value string
}

struct NameExpr {
	name string
}

struct CallExpr {
	func Expr
	args []Expr
}

struct AttributeExpr {
	value Expr
	attr string
}

struct SubscriptExpr {
	value Expr
	slice Expr
}

struct UnaryExpr {
	op string
	operand Expr
}

struct BinaryExpr {
	left Expr
	op string
	right Expr
}

struct BoolOpExpr {
	op string
	values []Expr
}

struct CompareExpr {
	left Expr
	ops []string
	comparators []Expr
}

struct MatchCase {
	pattern Pattern
	body Expr
}

struct MatchExpr {
	subject Expr
	cases []MatchCase
}

struct ValuePattern {
	value int
}

struct BindPattern {
	name string
}

struct WildcardPattern {}

struct ExprStmt {
	value Expr
}

struct AssignStmt {
	target string
	value Expr
}

struct PassStmt {}

struct BreakStmt {}

struct ContinueStmt {}

struct ReturnStmt {
	value ?Expr
}

struct IfStmt {
	test Expr
	body []Stmt
	orelse []Stmt
}

struct WhileStmt {
	test Expr
	body []Stmt
	orelse []Stmt
}

struct ForStmt {
	target string
	iter Expr
	body []Stmt
	orelse []Stmt
}

struct FunctionDefStmt {
	name string
	args []string
	body []Stmt
}

struct ClassDefStmt {
	name string
	bases []Expr
	body []Stmt
}

struct ImportAlias {
	name string
}

struct ImportStmt {
	names []ImportAlias
}

struct Module {
	body []Stmt
}

struct Lexer {
	source string
mut:
	pos int
	at_line_start bool = true
	indent_stack []int = [0]
	pending []Token
	brace_depth int
}

fn (mut l Lexer) next_token() !Token {
	for {
		if l.pending.len > 0 {
			tok := l.pending[0]
			l.pending = l.pending[1..]
			return tok
		}
		if l.pos >= l.source.len {
			if l.indent_stack.len > 1 {
				l.indent_stack = l.indent_stack[..l.indent_stack.len - 1]
				return Token{kind: .dedent, text: ''}
			}
			return Token{kind: .eof, text: ''}
		}
		if l.at_line_start && l.brace_depth == 0 {
			l.handle_indentation()!
			if l.pending.len > 0 {
				continue
			}
			if l.pos >= l.source.len {
				continue
			}
		}
		l.skip_inline_ws()
		if l.pos >= l.source.len {
			continue
		}
		ch := l.source[l.pos]
		if ch == `#` {
			l.skip_comment()
			continue
		}
		if ch == `\n` {
			l.pos++
			if l.brace_depth > 0 {
				continue
			}
			l.at_line_start = true
			return Token{kind: .newline, text: '\n'}
		}
		l.at_line_start = false

		if is_alpha(ch) {
			start := l.pos
			l.pos++
			for l.pos < l.source.len && is_alnum(l.source[l.pos]) {
				l.pos++
			}
			text := l.source[start..l.pos]
			return keyword_or_ident(text)
		}
		if is_digit(ch) {
			start := l.pos
			l.pos++
			for l.pos < l.source.len && is_digit(l.source[l.pos]) {
				l.pos++
			}
			return Token{kind: .int_lit, text: l.source[start..l.pos]}
		}
		if ch == `"` {
			l.pos++
			start := l.pos
			for l.pos < l.source.len && l.source[l.pos] != `"` {
				if l.source[l.pos] == `\\` && l.pos + 1 < l.source.len {
					l.pos += 2
					continue
				}
				if l.source[l.pos] == `\n` {
					return error('unterminated string literal')
				}
				l.pos++
			}
			if l.pos >= l.source.len {
				return error('unterminated string literal')
			}
			text := l.source[start..l.pos]
			l.pos++
			return Token{kind: .string_lit, text: unescape_string(text)}
		}

		l.pos++
		return match ch {
			`(` {
				l.brace_depth++
				Token{kind: .lparen, text: '('}
			}
			`)` {
				if l.brace_depth > 0 {
					l.brace_depth--
				}
				Token{kind: .rparen, text: ')'}
			}
			`{` {
				l.brace_depth++
				Token{kind: .lbrace, text: '{'}
			}
			`}` {
				if l.brace_depth > 0 {
					l.brace_depth--
				}
				Token{kind: .rbrace, text: '}'}
			}
			`[` {
				l.brace_depth++
				Token{kind: .lbracket, text: '['}
			}
			`]` {
				if l.brace_depth > 0 {
					l.brace_depth--
				}
				Token{kind: .rbracket, text: ']'}
			}
			`+` { Token{kind: .plus, text: '+'} }
			`-` { Token{kind: .minus, text: '-'} }
			`*` { Token{kind: .star, text: '*'} }
			`/` { Token{kind: .slash, text: '/'} }
			`,` { Token{kind: .comma, text: ','} }
			`.` { Token{kind: .dot, text: '.'} }
			`:` { Token{kind: .colon, text: ':'} }
			`<` {
				if l.pos < l.source.len && l.source[l.pos] == `=` {
					l.pos++
					Token{kind: .le, text: '<='}
				} else {
					Token{kind: .lt, text: '<'}
				}
			}
			`>` {
				if l.pos < l.source.len && l.source[l.pos] == `=` {
					l.pos++
					Token{kind: .ge, text: '>='}
				} else {
					Token{kind: .gt, text: '>'}
				}
			}
			`!` {
				if l.pos < l.source.len && l.source[l.pos] == `=` {
					l.pos++
					Token{kind: .noteq, text: '!='}
				} else {
					return error('unexpected token "!"')
				}
			}
			`=` {
				if l.pos < l.source.len && l.source[l.pos] == `=` {
					l.pos++
					Token{kind: .eqeq, text: '=='}
				} else {
					Token{kind: .assign, text: '='}
				}
			}
			else { return error('unexpected token "${rune(ch)}"') }
		}
	}
	return error('unreachable lexer state')
}

fn keyword_or_ident(text string) Token {
	return match text {
		'match' { Token{kind: .kw_match, text: text} }
		'import' { Token{kind: .kw_import, text: text} }
		'if' { Token{kind: .kw_if, text: text} }
		'else' { Token{kind: .kw_else, text: text} }
		'elif' { Token{kind: .kw_elif, text: text} }
		'pass' { Token{kind: .kw_pass, text: text} }
		'for' { Token{kind: .kw_for, text: text} }
		'in' { Token{kind: .kw_in, text: text} }
		'while' { Token{kind: .kw_while, text: text} }
		'break' { Token{kind: .kw_break, text: text} }
		'continue' { Token{kind: .kw_continue, text: text} }
		'return' { Token{kind: .kw_return, text: text} }
		'def' { Token{kind: .kw_def, text: text} }
		'class' { Token{kind: .kw_class, text: text} }
		'and' { Token{kind: .kw_and, text: text} }
		'or' { Token{kind: .kw_or, text: text} }
		'not' { Token{kind: .kw_not, text: text} }
		'_' { Token{kind: .underscore, text: text} }
		else { Token{kind: .ident, text: text} }
	}
}

fn (mut l Lexer) handle_indentation() ! {
	if l.brace_depth > 0 {
		return
	}
	mut i := l.pos
	mut spaces := 0
	for i < l.source.len {
		ch := l.source[i]
		if ch == ` ` {
			spaces++
			i++
			continue
		}
		if ch == `\t` {
			return error('tabs are not supported for indentation')
		}
		break
	}
	if i < l.source.len && l.source[i] == `#` {
		for i < l.source.len && l.source[i] != `\n` {
			i++
		}
	}
	if i < l.source.len && l.source[i] == `\n` {
		l.pos = i
		return
	}
	l.pos = i
	l.at_line_start = false

	curr := l.indent_stack[l.indent_stack.len - 1]
	if spaces > curr {
		l.indent_stack << spaces
		l.pending << Token{kind: .indent, text: ''}
		return
	}
	if spaces < curr {
		for l.indent_stack.len > 1 && l.indent_stack[l.indent_stack.len - 1] > spaces {
			l.indent_stack = l.indent_stack[..l.indent_stack.len - 1]
			l.pending << Token{kind: .dedent, text: ''}
		}
		if l.indent_stack[l.indent_stack.len - 1] != spaces {
			return error('inconsistent indentation')
		}
	}
}

fn (mut l Lexer) skip_inline_ws() {
	for l.pos < l.source.len {
		ch := l.source[l.pos]
		if ch == ` ` || ch == `\r` || ch == `\t` {
			l.pos++
			continue
		}
		break
	}
}

fn (mut l Lexer) skip_comment() {
	for l.pos < l.source.len && l.source[l.pos] != `\n` {
		l.pos++
	}
}

fn is_alpha(ch u8) bool {
	return (ch >= `a` && ch <= `z`) || (ch >= `A` && ch <= `Z`) || ch == `_`
}

fn is_alnum(ch u8) bool {
	return is_alpha(ch) || is_digit(ch)
}

fn is_digit(ch u8) bool {
	return ch >= `0` && ch <= `9`
}

fn unescape_string(s string) string {
	mut out := ''
	mut i := 0
	for i < s.len {
		if s[i] == `\\` && i + 1 < s.len {
			next := s[i + 1]
			out += match next {
				`n` { '\n' }
				`t` { '\t' }
				`"` { '"' }
				`\\` { '\\' }
				else { next.ascii_str() }
			}
			i += 2
			continue
		}
		out += s[i].ascii_str()
		i++
	}
	return out
}

struct Parser {
mut:
	lexer Lexer
	curr Token
	next Token
	skip_stmt_newline bool
}

fn new_parser(source string) !Parser {
	mut lexer := Lexer{source: source}
	first := lexer.next_token()!
	second := lexer.next_token()!
	return Parser{lexer: lexer, curr: first, next: second}
}

fn (mut p Parser) parse_expr_root() !Expr {
	expr := p.parse_expr()!
	for p.curr.kind == .newline {
		p.advance()!
	}
	p.expect(.eof)!
	return expr
}

fn (mut p Parser) parse_module() !Module {
	mut body := []Stmt{}
	p.consume_newlines()!
	for p.curr.kind != .eof {
		body << p.parse_stmt()!
		p.consume_newlines()!
	}
	return Module{body: body}
}

fn (mut p Parser) parse_stmt() !Stmt {
	return match p.curr.kind {
		.kw_if { p.parse_if_stmt() }
		.kw_while { p.parse_while_stmt() }
		.kw_for { p.parse_for_stmt() }
		.kw_def { p.parse_function_def() }
		.kw_class { p.parse_class_def() }
		else {
			stmt := p.parse_simple_stmt()!
			if p.skip_stmt_newline {
				p.skip_stmt_newline = false
			} else {
				p.expect(.newline)!
			}
			stmt
		}
	}
}

fn (mut p Parser) parse_if_stmt() !Stmt {
	p.expect(.kw_if)!
	test := p.parse_expr()!
	body := p.parse_suite()!
	mut orelse := []Stmt{}
	if p.curr.kind == .kw_else {
		p.advance()!
		orelse = p.parse_suite()!
	} else if p.curr.kind == .kw_elif {
		p.advance()!
		elif_test := p.parse_expr()!
		elif_body := p.parse_suite()!
		orelse = [Stmt(IfStmt{test: elif_test, body: elif_body, orelse: []Stmt{}})]
	}
	return IfStmt{test: test, body: body, orelse: orelse}
}

fn (mut p Parser) parse_while_stmt() !Stmt {
	p.expect(.kw_while)!
	test := p.parse_expr()!
	body := p.parse_suite()!
	mut orelse := []Stmt{}
	if p.curr.kind == .kw_else {
		p.advance()!
		orelse = p.parse_suite()!
	}
	return WhileStmt{test: test, body: body, orelse: orelse}
}

fn (mut p Parser) parse_for_stmt() !Stmt {
	p.expect(.kw_for)!
	if p.curr.kind != .ident {
		return error('expected loop variable name in for statement')
	}
	target := p.curr.text
	p.advance()!
	p.expect(.kw_in)!
	iter := p.parse_expr()!
	body := p.parse_suite()!
	mut orelse := []Stmt{}
	if p.curr.kind == .kw_else {
		p.advance()!
		orelse = p.parse_suite()!
	}
	return ForStmt{target: target, iter: iter, body: body, orelse: orelse}
}

fn (mut p Parser) parse_function_def() !Stmt {
	p.expect(.kw_def)!
	if p.curr.kind != .ident {
		return error('expected function name')
	}
	name := p.curr.text
	p.advance()!
	p.expect(.lparen)!
	mut args := []string{}
	if p.curr.kind != .rparen {
		if p.curr.kind != .ident {
			return error('expected parameter name')
		}
		args << p.curr.text
		p.advance()!
		for p.curr.kind == .comma {
			p.advance()!
			if p.curr.kind == .rparen {
				break
			}
			if p.curr.kind != .ident {
				return error('expected parameter name')
			}
			args << p.curr.text
			p.advance()!
		}
	}
	p.expect(.rparen)!
	body := p.parse_suite()!
	return FunctionDefStmt{name: name, args: args, body: body}
}

fn (mut p Parser) parse_class_def() !Stmt {
	p.expect(.kw_class)!
	if p.curr.kind != .ident {
		return error('expected class name')
	}
	name := p.curr.text
	p.advance()!
	mut bases := []Expr{}
	if p.curr.kind == .lparen {
		p.advance()!
		if p.curr.kind != .rparen {
			bases << p.parse_expr()!
			for p.curr.kind == .comma {
				p.advance()!
				if p.curr.kind == .rparen {
					break
				}
				bases << p.parse_expr()!
			}
		}
		p.expect(.rparen)!
	}
	body := p.parse_suite()!
	return ClassDefStmt{name: name, bases: bases, body: body}
}

fn (mut p Parser) parse_suite() ![]Stmt {
	p.expect(.colon)!
	p.expect(.newline)!
	p.expect(.indent)!
	mut body := []Stmt{}
	p.consume_newlines()!
	for p.curr.kind != .dedent && p.curr.kind != .eof {
		body << p.parse_stmt()!
		p.consume_newlines()!
	}
	if body.len == 0 {
		return error('expected at least one statement in block')
	}
	p.expect(.dedent)!
	return body
}

fn (mut p Parser) parse_simple_stmt() !Stmt {
	if p.curr.kind == .kw_import {
		return p.parse_import_stmt()
	}
	if p.curr.kind == .kw_pass {
		p.advance()!
		return PassStmt{}
	}
	if p.curr.kind == .kw_break {
		p.advance()!
		return BreakStmt{}
	}
	if p.curr.kind == .kw_continue {
		p.advance()!
		return ContinueStmt{}
	}
	if p.curr.kind == .kw_return {
		p.advance()!
		if p.curr.kind == .newline {
			return ReturnStmt{value: none}
		}
		value := p.parse_expr()!
		return ReturnStmt{value: value}
	}
	if p.curr.kind == .ident && p.next.kind == .assign {
		target := p.curr.text
		p.advance()!
		p.expect(.assign)!
		value := p.parse_expr()!
		return AssignStmt{target: target, value: value}
	}
	expr := p.parse_expr()!
	return ExprStmt{value: expr}
}

fn (mut p Parser) parse_import_stmt() !Stmt {
	p.expect(.kw_import)!
	mut names := []ImportAlias{}
	names << ImportAlias{name: p.parse_dotted_name()!}
	for p.curr.kind == .comma {
		p.advance()!
		names << ImportAlias{name: p.parse_dotted_name()!}
	}
	return ImportStmt{names: names}
}

fn (mut p Parser) parse_dotted_name() !string {
	if p.curr.kind != .ident {
		return error('expected import name, found ${p.curr.kind}')
	}
	mut name := p.curr.text
	p.advance()!
	for p.curr.kind == .dot {
		p.advance()!
		if p.curr.kind != .ident {
			return error('expected identifier after dot in import')
		}
		name += '.' + p.curr.text
		p.advance()!
	}
	return name
}

fn (mut p Parser) parse_expr() !Expr {
	return p.parse_or_expr()
}

fn (mut p Parser) parse_or_expr() !Expr {
	mut left := p.parse_and_expr()!
	if p.curr.kind != .kw_or {
		return left
	}
	mut values := [left]
	for p.curr.kind == .kw_or {
		p.advance()!
		values << p.parse_and_expr()!
	}
	return BoolOpExpr{op: 'Or', values: values}
}

fn (mut p Parser) parse_and_expr() !Expr {
	mut left := p.parse_not_expr()!
	if p.curr.kind != .kw_and {
		return left
	}
	mut values := [left]
	for p.curr.kind == .kw_and {
		p.advance()!
		values << p.parse_not_expr()!
	}
	return BoolOpExpr{op: 'And', values: values}
}

fn (mut p Parser) parse_not_expr() !Expr {
	if p.curr.kind == .kw_not {
		p.advance()!
		operand := p.parse_not_expr()!
		return UnaryExpr{op: 'Not', operand: operand}
	}
	return p.parse_comparison_expr()
}

fn (mut p Parser) parse_comparison_expr() !Expr {
	left := p.parse_additive()!
	if !is_comparison_op(p.curr.kind) {
		return left
	}
	mut ops := []string{}
	mut comparators := []Expr{}
	for is_comparison_op(p.curr.kind) {
		ops << comparison_op_name(p.curr.kind)
		p.advance()!
		comparators << p.parse_additive()!
	}
	return CompareExpr{left: left, ops: ops, comparators: comparators}
}

fn is_comparison_op(kind TokenKind) bool {
	return kind == .lt || kind == .gt || kind == .le || kind == .ge || kind == .eqeq || kind == .noteq
}

fn comparison_op_name(kind TokenKind) string {
	return match kind {
		.lt { 'Lt' }
		.gt { 'Gt' }
		.le { 'LtE' }
		.ge { 'GtE' }
		.eqeq { 'Eq' }
		.noteq { 'NotEq' }
		else { 'Unknown' }
	}
}

fn (mut p Parser) parse_additive() !Expr {
	mut left := p.parse_multiplicative()!
	for p.curr.kind == .plus || p.curr.kind == .minus {
		op := if p.curr.kind == .plus { 'Add' } else { 'Sub' }
		p.advance()!
		right := p.parse_multiplicative()!
		left = BinaryExpr{left: left, op: op, right: right}
	}
	return left
}

fn (mut p Parser) parse_multiplicative() !Expr {
	mut left := p.parse_unary()!
	for p.curr.kind == .star || p.curr.kind == .slash {
		op := if p.curr.kind == .star { 'Mult' } else { 'Div' }
		p.advance()!
		right := p.parse_unary()!
		left = BinaryExpr{left: left, op: op, right: right}
	}
	return left
}

fn (mut p Parser) parse_unary() !Expr {
	if p.curr.kind == .plus {
		p.advance()!
		operand := p.parse_unary()!
		return UnaryExpr{op: 'UAdd', operand: operand}
	}
	if p.curr.kind == .minus {
		p.advance()!
		operand := p.parse_unary()!
		return UnaryExpr{op: 'USub', operand: operand}
	}
	return p.parse_postfix()
}

fn (mut p Parser) parse_postfix() !Expr {
	mut expr := p.parse_primary()!
	for {
		if p.curr.kind == .lparen {
			p.advance()!
			mut args := []Expr{}
			if p.curr.kind != .rparen {
				args << p.parse_expr()!
				for p.curr.kind == .comma {
					p.advance()!
					if p.curr.kind == .rparen {
						break
					}
					args << p.parse_expr()!
				}
			}
			p.expect(.rparen)!
			expr = CallExpr{func: expr, args: args}
			continue
		}
		if p.curr.kind == .dot {
			p.advance()!
			if p.curr.kind != .ident {
				return error('expected attribute name after dot')
			}
			attr := p.curr.text
			p.advance()!
			expr = AttributeExpr{value: expr, attr: attr}
			continue
		}
		if p.curr.kind == .lbracket {
			p.advance()!
			slice := p.parse_expr()!
			p.expect(.rbracket)!
			expr = SubscriptExpr{value: expr, slice: slice}
			continue
		}
		break
	}
	return expr
}

fn (mut p Parser) parse_primary() !Expr {
	if p.curr.kind == .kw_match {
		return p.parse_match_expr()
	}
	return match p.curr.kind {
		.int_lit {
			value := strconv.atoi(p.curr.text) or { return error('invalid integer literal') }
			p.advance()!
			IntExpr{value: value}
		}
		.string_lit {
			value := p.curr.text
			p.advance()!
			StringExpr{value: value}
		}
		.ident {
			name := p.curr.text
			p.advance()!
			NameExpr{name: name}
		}
		.lparen {
			p.advance()!
			expr := p.parse_expr()!
			p.expect(.rparen)!
			expr
		}
		else {
			return error('expected expression, found ${p.curr.kind}')
		}
	}
}

fn (mut p Parser) parse_match_expr() !Expr {
	p.expect(.kw_match)!
	subject := p.parse_expr()!
	if p.curr.kind == .colon {
		return p.parse_indented_match_cases(subject)
	}
	return error('expected ":" after match subject')
}

fn (mut p Parser) parse_indented_match_cases(subject Expr) !Expr {
	p.expect(.colon)!
	p.expect(.newline)!
	p.expect(.indent)!
	mut cases := []MatchCase{}
	p.consume_newlines()!
	for is_pattern_start(p.curr.kind) {
		pattern := p.parse_pattern()!
		p.expect(.colon)!
		body := p.parse_expr()!
		p.expect(.newline)!
		p.consume_newlines()!
		cases << MatchCase{pattern: pattern, body: body}
	}
	if cases.len == 0 {
		return error('indented match expression needs at least one case')
	}
	p.expect(.dedent)!
	p.skip_stmt_newline = true
	return MatchExpr{subject: subject, cases: cases}
}

fn (mut p Parser) parse_pattern() !Pattern {
	return match p.curr.kind {
		.underscore {
			p.advance()!
			WildcardPattern{}
		}
		.int_lit {
			value := strconv.atoi(p.curr.text) or { return error('invalid integer literal') }
			p.advance()!
			ValuePattern{value: value}
		}
		.ident {
			name := p.curr.text
			p.advance()!
			BindPattern{name: name}
		}
		else { return error('expected pattern, found ${p.curr.kind}') }
	}
}

fn is_pattern_start(kind TokenKind) bool {
	return kind == .underscore || kind == .int_lit || kind == .ident
}

fn (mut p Parser) consume_newlines() ! {
	for p.curr.kind == .newline {
		p.advance()!
	}
}

fn (mut p Parser) expect(kind TokenKind) ! {
	if p.curr.kind != kind {
		return error('expected ${kind}, found ${p.curr.kind}')
	}
	p.advance()!
}

fn (mut p Parser) advance() ! {
	p.curr = p.next
	p.next = p.lexer.next_token()!
}

fn json_escape(s string) string {
	mut out := ''
	for i := 0; i < s.len; i++ {
		ch := s[i]
		out += match ch {
			`\\` { '\\\\' }
			`"` { '\\"' }
			`\n` { '\\n' }
			`\t` { '\\t' }
			else { ch.ascii_str() }
		}
	}
	return out
}

fn expr_json(expr Expr) string {
	return match expr {
		IntExpr { '{"type":"Constant","value":${expr.value}}' }
		StringExpr { '{"type":"Constant","value":"${json_escape(expr.value)}"}' }
		NameExpr { '{"type":"Name","id":"${json_escape(expr.name)}"}' }
		CallExpr {
			mut args_json := []string{}
			for a in expr.args {
				args_json << expr_json(a)
			}
			'{"type":"Call","func":${expr_json(expr.func)},"args":[${args_json.join(",")}]} '
		}
		AttributeExpr {
			'{"type":"Attribute","value":${expr_json(expr.value)},"attr":"${json_escape(expr.attr)}"}'
		}
		SubscriptExpr {
			'{"type":"Subscript","value":${expr_json(expr.value)},"slice":${expr_json(expr.slice)}}'
		}
		UnaryExpr { '{"type":"UnaryOp","op":"${expr.op}","operand":${expr_json(expr.operand)}}' }
		BinaryExpr {
			'{"type":"BinOp","left":${expr_json(expr.left)},"op":"${expr.op}","right":${expr_json(expr.right)}}'
		}
		BoolOpExpr {
			mut values_json := []string{}
			for v in expr.values {
				values_json << expr_json(v)
			}
			'{"type":"BoolOp","op":"${expr.op}","values":[${values_json.join(",")}]} '
		}
		CompareExpr {
			mut ops_json := []string{}
			for op in expr.ops {
				ops_json << '"${op}"'
			}
			mut cmps_json := []string{}
			for c in expr.comparators {
				cmps_json << expr_json(c)
			}
			'{"type":"Compare","left":${expr_json(expr.left)},"ops":[${ops_json.join(",")}],"comparators":[${cmps_json.join(",")}]} '
		}
		MatchExpr {
			mut cases_json := []string{}
			for item in expr.cases {
				cases_json << '{"type":"match_case","pattern":${pattern_json(item.pattern)},"body":${expr_json(item.body)}}'
			}
			'{"type":"Match","subject":${expr_json(expr.subject)},"cases":[${cases_json.join(",")}]} '
		}
	}
}

fn pattern_json(pattern Pattern) string {
	return match pattern {
		WildcardPattern { '{"type":"MatchAs","name":null}' }
		BindPattern { '{"type":"MatchAs","name":"${json_escape(pattern.name)}"}' }
		ValuePattern { '{"type":"MatchValue","value":{"type":"Constant","value":${pattern.value}}}' }
	}
}

fn stmt_json(stmt Stmt) string {
	return match stmt {
		ExprStmt { '{"type":"Expr","value":${expr_json(stmt.value)}}' }
		ImportStmt {
			mut names_json := []string{}
			for n in stmt.names {
				names_json << '{"type":"alias","name":"${json_escape(n.name)}"}'
			}
			'{"type":"Import","names":[${names_json.join(",")}]} '
		}
		AssignStmt {
			'{"type":"Assign","target":"${json_escape(stmt.target)}","value":${expr_json(stmt.value)}}'
		}
		PassStmt { '{"type":"Pass"}' }
		BreakStmt { '{"type":"Break"}' }
		ContinueStmt { '{"type":"Continue"}' }
		ReturnStmt {
			if value := stmt.value {
				'{"type":"Return","value":${expr_json(value)}}'
			} else {
				'{"type":"Return","value":null}'
			}
		}
		IfStmt {
			mut body_json := []string{}
			for s in stmt.body {
				body_json << stmt_json(s)
			}
			mut orelse_json := []string{}
			for s in stmt.orelse {
				orelse_json << stmt_json(s)
			}
			'{"type":"If","test":${expr_json(stmt.test)},"body":[${body_json.join(",")}],"orelse":[${orelse_json.join(",")}]} '
		}
		WhileStmt {
			mut body_json := []string{}
			for s in stmt.body {
				body_json << stmt_json(s)
			}
			mut orelse_json := []string{}
			for s in stmt.orelse {
				orelse_json << stmt_json(s)
			}
			'{"type":"While","test":${expr_json(stmt.test)},"body":[${body_json.join(",")}],"orelse":[${orelse_json.join(",")}]} '
		}
		ForStmt {
			mut body_json := []string{}
			for s in stmt.body {
				body_json << stmt_json(s)
			}
			mut orelse_json := []string{}
			for s in stmt.orelse {
				orelse_json << stmt_json(s)
			}
			'{"type":"For","target":"${json_escape(stmt.target)}","iter":${expr_json(stmt.iter)},"body":[${body_json.join(",")}],"orelse":[${orelse_json.join(",")}]} '
		}
		FunctionDefStmt {
			mut args_json := []string{}
			for a in stmt.args {
				args_json << '"${json_escape(a)}"'
			}
			mut body_json := []string{}
			for s in stmt.body {
				body_json << stmt_json(s)
			}
			'{"type":"FunctionDef","name":"${json_escape(stmt.name)}","args":[${args_json.join(",")}],"body":[${body_json.join(",")}]} '
		}
		ClassDefStmt {
			mut bases_json := []string{}
			for b in stmt.bases {
				bases_json << expr_json(b)
			}
			mut body_json := []string{}
			for s in stmt.body {
				body_json << stmt_json(s)
			}
			'{"type":"ClassDef","name":"${json_escape(stmt.name)}","bases":[${bases_json.join(",")}],"body":[${body_json.join(",")}]} '
		}
	}
}

fn module_json(mod Module) string {
	mut body_json := []string{}
	for s in mod.body {
		body_json << stmt_json(s)
	}
	return '{"type":"Module","body":[${body_json.join(",")}]} '
}
