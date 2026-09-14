from solution import solve
def test_overlap(): assert solve([(3,5),(1,4)]) == [(1,5)]
def test_touching(): assert solve([(1,2),(2,3)]) == [(1,3)]
def test_separate(): assert solve([(5,6),(1,2)]) == [(1,2),(5,6)]
