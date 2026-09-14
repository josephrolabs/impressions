from solution import solve
def test_words(): assert solve('a b c') == 'c b a'
def test_space(): assert solve('  a   b ') == 'b a'
def test_empty(): assert solve('') == ''
