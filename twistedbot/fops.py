

ABS_TOL = 0.000001
REL_TOL = 0.000001


def eq_abs(a, b):
	return abs(a - b) <= ABS_TOL * max(1.0, max(abs(a), abs(b)))


def eq(a, b):
	return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))

def lt(a, b):
	if eq(a, b):
		return False
	return a < b

def gt(a, b):
	if eq(a, b):
		return False
	return a > b

def gte(a, b):
	if eq(a, b):
		return True
	return a > b

def lte(a, b):
	if eq(a, b):
		return True
	return a < b

def eqzero(a):
	return eq(a, 0)


def test(a, b):
	if eq(a, b):
		print "EQ\t%.50f -> %.50f" % (a, b)
		return
	print "RUN\t%.50f -> %.50f" % (a, b)
	o = a
	d = b - a
	a += d
	print "STEP 1\t%.50f" % a
	print "DIFF \t%.50f" % (a - b,)
	print eq(a, b)
	print


def man_test():
	test(0.7, 0.1)
	test(0.1, 0.7)
	test(-0.7, -0.1)
	test(-0.1, -0.7)
	test(700000, 0.1)
	test(0.1, 0.7)

if __name__ == '__main__':
	vals = [72.0025, 72.0] #[7.1, 0.73, 0.19, -0.15, -0.757, -7.99, 72.0025, 72.0]
	for a in vals:
		for b in vals:
			if abs(a) == abs(b): continue
			test(a, b)
