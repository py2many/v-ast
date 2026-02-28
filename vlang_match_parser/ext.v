module main

__global (
	g_last_json string
	g_last_error string
)

@[export: 'v_ast_parse_module_json']
pub fn v_ast_parse_module_json(source &char) &char {
	g_last_error = ''
	src := unsafe { cstring_to_vstring(source) }
	mut parser := new_parser(src) or {
		g_last_error = 'parse setup error: ${err}'
		return unsafe { nil }
	}
	mod := parser.parse_module() or {
		g_last_error = 'parse error: ${err}'
		return unsafe { nil }
	}
	g_last_json = module_json(mod)
	return g_last_json.str
}

@[export: 'v_ast_parse_expression_json']
pub fn v_ast_parse_expression_json(source &char) &char {
	g_last_error = ''
	src := unsafe { cstring_to_vstring(source) }
	mut parser := new_parser(src) or {
		g_last_error = 'parse setup error: ${err}'
		return unsafe { nil }
	}
	expr := parser.parse_expr_root() or {
		g_last_error = 'parse error: ${err}'
		return unsafe { nil }
	}
	g_last_json = expr_json(expr)
	return g_last_json.str
}

@[export: 'v_ast_last_error']
pub fn v_ast_last_error() &char {
	return g_last_error.str
}
