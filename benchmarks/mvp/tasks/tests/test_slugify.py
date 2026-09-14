from solution import solve
def test_words(): assert solve('Hello World') == 'hello-world'
def test_symbols(): assert solve('A -- B!') == 'a-b'
def test_edges(): assert solve('  hi  ') == 'hi'
