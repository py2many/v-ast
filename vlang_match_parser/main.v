module main

import os

fn main() {
	args := os.args[1..]
	if args.len < 2 {
		eprintln('usage: v run vlang_match_parser --json <source-file> | --json-expr <source-file>')
		exit(2)
	}
	mode := args[0]
	source_path := args[1]
	source := os.read_file(source_path) or {
		eprintln('failed to read ${source_path}: ${err}')
		exit(1)
	}
	mut parser := new_parser(source) or {
		eprintln('parse setup error: ${err}')
		exit(1)
	}
	if mode == '--json' {
		mod := parser.parse_module() or {
			eprintln('parse error: ${err}')
			exit(1)
		}
		println(module_json(mod).trim_space())
		return
	}
	if mode == '--json-expr' {
		expr := parser.parse_expr_root() or {
			eprintln('parse error: ${err}')
			exit(1)
		}
		println(expr_json(expr).trim_space())
		return
	}
	eprintln('unknown mode: ${mode}')
	exit(2)
}
