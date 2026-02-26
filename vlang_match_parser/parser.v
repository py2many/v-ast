module main

import strconv

enum TokenKind {
	eof
	ident
	int_lit
	kw_match
	kw_case
	underscore
	lparen
	rparen
	lbrace
	rbrace
	plus
	minus
	star
	slash
	arrow
	comma
}

struct Token {
	kind TokenKind
	text string
}

type Expr = BinaryExpr | IntExpr | MatchExpr | NameExpr

type Pattern = BindPattern | ValuePattern | WildcardPattern

struct IntExpr {
	value int
}

struct NameExpr {
	name string
}

struct BinaryExpr {
	left Expr
	op string
	right Expr
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

struct Lexer {
	source string
mut:
	pos int
}

fn (mut l Lexer) next_token() !Token {
	l.skip_ws()
	if l.pos >= l.source.len {
		return Token{kind: .eof, text: ''}
	}
	ch := l.source[l.pos]
	if is_alpha(ch) {
		start := l.pos
		l.pos++
		for l.pos < l.source.len && is_alnum(l.source[l.pos]) {
			l.pos++
		}
		text := l.source[start..l.pos]
		return match text {
			'match' { Token{kind: .kw_match, text: text} }
			'case' { Token{kind: .kw_case, text: text} }
			'_' { Token{kind: .underscore, text: text} }
			else { Token{kind: .ident, text: text} }
		}
	}
	if is_digit(ch) {
		start := l.pos
		l.pos++
		for l.pos < l.source.len && is_digit(l.source[l.pos]) {
			l.pos++
		}
		return Token{kind: .int_lit, text: l.source[start..l.pos]}
	}
	l.pos++
	return match ch {
		`(` { Token{kind: .lparen, text: '('} }
		`)` { Token{kind: .rparen, text: ')'} }
		`{` { Token{kind: .lbrace, text: '{'} }
		`}` { Token{kind: .rbrace, text: '}'} }
		`+` { Token{kind: .plus, text: '+'} }
		`-` { Token{kind: .minus, text: '-'} }
		`*` { Token{kind: .star, text: '*'} }
		`/` { Token{kind: .slash, text: '/'} }
		`,` { Token{kind: .comma, text: ','} }
		`=` {
			if l.pos < l.source.len && l.source[l.pos] == `>` {
				l.pos++
				Token{kind: .arrow, text: '=>'}
			} else {
				return error('unexpected token "="')
			}
		}
		else { return error('unexpected token "${rune(ch)}"') }
	}
}

fn (mut l Lexer) skip_ws() {
	for l.pos < l.source.len {
		ch := l.source[l.pos]
		if ch == ` ` || ch == `\n` || ch == `\r` || ch == `\t` {
			l.pos++
			continue
		}
		break
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

struct Parser {
	mut:
	lexer Lexer
	curr Token
}

fn new_parser(source string) !Parser {
	mut lexer := Lexer{source: source}
	first := lexer.next_token()!
	return Parser{
		lexer: lexer
		curr: first
	}
}

fn (mut p Parser) parse() !Expr {
	expr := p.parse_expr()!
	p.expect(.eof)!
	return expr
}

fn (mut p Parser) parse_expr() !Expr {
	if p.curr.kind == .kw_match {
		return p.parse_match_expr()
	}
	return p.parse_additive()
}

fn (mut p Parser) parse_match_expr() !Expr {
	p.expect(.kw_match)!
	subject := p.parse_additive()!
	p.expect(.lbrace)!
	mut cases := []MatchCase{}
	for p.curr.kind == .kw_case {
		p.advance()!
		pattern := p.parse_pattern()!
		p.expect(.arrow)!
		body := p.parse_expr()!
		if p.curr.kind == .comma {
			p.advance()!
		}
		cases << MatchCase{pattern: pattern, body: body}
	}
	if cases.len == 0 {
		return error('match expression needs at least one case')
	}
	p.expect(.rbrace)!
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
	mut left := p.parse_primary()!
	for p.curr.kind == .star || p.curr.kind == .slash {
		op := if p.curr.kind == .star { 'Mult' } else { 'Div' }
		p.advance()!
		right := p.parse_primary()!
		left = BinaryExpr{left: left, op: op, right: right}
	}
	return left
}

fn (mut p Parser) parse_primary() !Expr {
	return match p.curr.kind {
		.int_lit {
			value := strconv.atoi(p.curr.text) or { return error('invalid integer literal') }
			p.advance()!
			IntExpr{value: value}
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

fn (mut p Parser) expect(kind TokenKind) ! {
	if p.curr.kind != kind {
		return error('expected ${kind}, found ${p.curr.kind}')
	}
	p.advance()!
}

fn (mut p Parser) advance() ! {
	p.curr = p.lexer.next_token()!
}

fn expr_json(expr Expr) string {
	return match expr {
		IntExpr { '{"type":"Constant","value":${expr.value}}' }
		NameExpr { '{"type":"Name","id":"${expr.name}"}' }
		BinaryExpr {
			'{"type":"BinOp","left":${expr_json(expr.left)},"op":"${expr.op}","right":${expr_json(expr.right)}}'
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
		BindPattern { '{"type":"MatchAs","name":"${pattern.name}"}' }
		ValuePattern { '{"type":"MatchValue","value":{"type":"Constant","value":${pattern.value}}}' }
	}
}
