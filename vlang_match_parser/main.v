module main

import os

fn main() {
	args := os.args[1..]
	if args.len < 2 || args[0] != '--json' {
		eprintln('usage: v run vlang_match_parser/main.v --json <source-file>')
		exit(2)
	}
	source_path := args[1]
	source := os.read_file(source_path) or {
		eprintln('failed to read ${source_path}: ${err}')
		exit(1)
	}
	mut parser := new_parser(source) or {
		eprintln('parse setup error: ${err}')
		exit(1)
	}
	expr := parser.parse() or {
		eprintln('parse error: ${err}')
		exit(1)
	}
	println(expr_json(expr).trim_space())
}
