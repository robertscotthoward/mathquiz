import datetime
import io
import os
import json
import random
import re
import time
import itertools
from fractions import gcd
import yaml

'''
Kind of like flash cards, where a card might say "3 + 8 = ?"
There's addition, subtraction, multiplication, division, normalized fractions, and negative numbers.
'''

CONFIG_FILENAME = "MathQuiz.sessions"
YAML_FILENAME = "MathQuiz.yaml"

# The number of questions you got right in a row.
conseqright = 0

test = False

# Include negative numbers?
negatives = False

onlymax = False

numbers = range(1,13)

def primes():
    """ Generate an infinite sequence of prime numbers.
    """
    # Maps composites to primes witnessing their compositeness.
    # This is memory efficient, as the sieve is not "run forward"
    # indefinitely, but only as long as required by the current
    # number being tested.
    #
    D = {}
    
    # The running integer that's checked for primeness
    q = 2
    
    while True:
        if q not in D:
            # q is a new prime.
            # Yield it and mark its first multiple that isn't
            # already marked in previous iterations
            # 
            yield q
            D[q * q] = [q]
        else:
            # q is composite. D[q] is the list of primes that
            # divide it. Since we've reached q, we no longer
            # need it in the map, but we'll mark the next 
            # multiples of its witnesses to prepare for larger
            # numbers
            # 
            for p in D[q]:
                D.setdefault(p + q, []).append(p)
            del D[q]
        
        q += 1


# Pick a random card and delete it from the list.
def pick(s):
    if test:
        i = 0
    else:
        i = random.randint(0, len(s) - 1)
    c = s[i]
    del s[i]
    return c

# Return all the factors of x
def factors(x):
    f = []
    i = 2
    while x > 1:
        if x % i == 0:
            f.append(i)
            x /= i
        else:
            i += 1 if i == 2 else 2
    return f

# Return the decimal value of x where x is a list in the format [X,Y,Z] where Y and Z are optional. 
# This represents a fraction 3+1/5 as [3,1,5] or 3 as [3]
def v3(x):
    if not len(x) in [1,3]: return -1
    if len(x) == 1: return float(x[0])
    return float(x[0]) + float(x[1]) / float(x[2])

# Return 1 if x == y, 0 if close; e.g. 3/6 instead of 1/2, and -1 if wrong.
def equals(op, x, y):
    if op == 'F':
        x = eval(x)
        y = eval(y)
        if isinstance(x, basestring):
            x = [int(q) for q in x]
        if len(x) != len(y):
            return -1
        for z in x:
            if not z in y:
                return -1
            y.remove(z)
        return 1 if len(y) == 0 else 0
    elif op == '/':
        # Remove all but digits and spaces and split on whitespace words.
        x = re.sub("[^0-9]", " ", x).split()
        y = re.sub("[^0-9]", " ", y).split()

        if v3(x) != v3(y):
            return -1
        if len(x) == 1: return 1
        return 1 if gcd(int(x[1]), int(x[2])) == 1 else 0
            
    else:
        return 1 if x.strip() == y.strip() else -1

def GetOp(op):
    return next(x for x in yaml['operators'] if x['abbr'] == op)

def Authenticate():
    while True:
        p = [Per(x) for x in yaml['people']]
        people = ', '.join(p)
        print("""
MATH TEST

What is your name? {0}, (Q)uit: """.format(people)),
        abbr = input().strip().upper()
        if abbr.upper() == 'Q':
            return ''
        person = next((x for x in yaml['people'] if x['abbr'] == abbr), None)
        if person != None:
            name = person['name']
            break
    print("Welcome {0}".format(person['name']))
    return name


def main():
    global conseqright
    conseqright = 0

    # Create a deck of test cards
    cards = []
    lo = 2
    hi = 12
    negdifficulty = GetOp('-')['difficulty']
    for op in ops:
        range1 = range(2, 10)
        yop = GetOp(op)
        lo = yop['lo'] if 'lo' in yop else 1
        hi = yop['hi'] if 'hi' in yop else 12
        difficulty = yop['difficulty']
        if negatives:
            lo = -hi
        if op == "F":
            for x in numbers:
                for y in range1:
                    for z in range(1,10):
                        points = difficulty
                        if x < 0 or y < 0:
                            points += negdifficulty
                        cards.append((op, x*y*z, factors(x*y*z), points))
        else:
            for x in range(lo,(max(numbers) if onlymax else hi)+1):
                for y in numbers:
                    points = difficulty
                    if x < 0 or y < 0:
                        points += negdifficulty
                    if op == "/":
                        for r in range(1 if "F" in ops else 0, y):
                            cards.append((op,x,(y, r), points))
                    else:
                        cards.append((op,x,y,points))

    # Start showing the cards
    print("Enter (Q) to quit and see your score")
    while len(cards) > 0:
        card = pick(cards)
        op, x, y, points = card
        # Points go up one per card for each 4 you get an a row
        q = min(10,int(conseqright / 4))
        points += q
        pre = "{0} cards left. Score is {1} [{2}]".format(len(cards), session['score'], points)
        if op == "A":
            prompt = "\n{0:<20}: {1:>3} + {2:>3} = ".format(pre, x, y)
            answer = x + y
        elif op == "S":
            prompt = "\n{0:<20}: {1:>3} - {2:>3} = ".format(pre, x + y, x)
            answer = y
        elif op == "M":
            prompt = "\n{0:<20}: {1:>3} X {2:>3} = ".format(pre, x, y)
            answer = x * y
        elif op == "D":
            prompt = "\n{0:<20}: {1:>3} / {2:>3} = ".format(pre, x * y, x)
            answer = y
        elif op == "F":
            prompt = "\n{0:<20}: factors of {1} = ".format(pre, x)
            answer = y
        elif op == "/":
            y,r = y
            prompt = "\n{0:<20}: {1:>3} / {2:>3} = ".format(pre, x * y + r, y)
            g = gcd(r,y)
            answer = "{0:>2}".format(x) if r == 0 else "{0:>2} {1}/{2}".format(x,r/g,y/g)
        answer = str(answer)

        if test:
            guess = answer
            print(prompt),
            print(guess),
        else:
            while True:
                print(prompt),
                guess = input().strip()
                if guess != '':
                    guess = ' '.join(guess.split()) # Replace multiple spaces with a single space
                    break
                

        if guess.upper() == "Q":
            return


        # Did you guess right?
        ans = equals(op, guess, answer)
        if ans == 1:
            # Yes. Your score increases by the amount of previous cards you got right in a row.
            session['right'] += 1
            session['score'] += points
            conseqright += 1
        elif ans == 0:
            # No. So show the answer and push two copies on deck.
            print("  ----> {0} with partial credit.".format(answer))
            session['wrong'] += 1
            cards.append(card)

            # Your score gets subtracted by the half the number of points for this card.
            session['score'] -= max(1,int(points/2))
        else:
            # No. So show the answer and push two copies on deck.
            print("  ----> {0}".format(answer))
            session['wrong'] += 1
            cards.append(card)
            cards.append(card)

            # Your score gets subtracted by the half the number of points for this card.
            session['score'] -= max(1,int(points/2))
            conseqright = 0


def scores(top = 0):
    print('''
HIGH SCORES:
Name                 Type       Right Wrong Score         Dollars When
==================== ========== ===== ===== ========== ========== ==============
''')
    for i, session in enumerate(sorted(config['sessions'], lambda x,y: x['score'] > y['score'])):
        # {'right': 144, 'name': 'Dagny', 'turns': 0, 'wrong': 0, 'score': 10440, 'type': 'a!'}
        ss = session
        ss['money'] = ss['score'] / 1000.0
        if not 'when' in ss: ss['when'] = ''
        print("{name:<20} {type:<10} {right:>5d} {wrong:>5d} {score:>10,d} {money:>10,.2f} {when:<14}".format(**ss))
        if top > 0 and i > top:
            break

def totals():
    print('''
HIGH SCORES:
Name                 Type       Right Wrong Score         Dollars When
==================== ========== ===== ===== ========== ========== ==============
''')
    users = {}
    for session in config['sessions']:
      name = session['name']
      if name in users:
        user = users[name]
      else:
        user = session
        user["right"] = 0
        user["wrong"] = 0
        user["score"] = 0
        user["money"] = 0
        users[name] = user

      user["right"] += session["right"]
      user["wrong"] += session["wrong"]
      user["score"] += session.get("score",0)
      #user["money"] += session.get("money",0)
      user["when"] = max(user.get("when",""), session.get("when",""))

    for i, k in enumerate(sorted(users)):
        ss = users[k]
        ss['money'] = ss['score'] / 1000.0
        if not 'when' in ss: ss['when'] = ''
        print("{name:<20} {type:<10} {right:>5d} {wrong:>5d} {score:>10,d} {money:>10,.2f} {when:<14}".format(**ss))


def Per(y):
    c = y['abbr']
    n = y['name']
    if c.upper() == n[0].upper():
        return "({0}){1}".format(c,n[1:])
    else:
        return "({0}) {1}".format(c,n)

if __name__ == "__main__":
    print([x for x in itertools.islice(primes(),0,10)])

    if os.path.isfile(CONFIG_FILENAME):
        with open(CONFIG_FILENAME) as f:
            config = json.load(f)
            totals()
    else:
        config = {'sessions': []}

    with open(YAML_FILENAME, 'r') as f:
        yaml = yaml.safe_load(f)

    while True:
        name = Authenticate()
        if name == '':
            break # You hit 'Q' to quit.

        start = time.time()
        loop = True
        
        while loop:
            negatives = False
            print("""
  (A)ddition
  (S)ubtraction
  (M)ultiplication
  (D)ivision
  (/) Division with fractions
  (F)actors; e.g. 12 = "2 2 3"
  (*) all of the above

  (N)egative numbers too
  (@) only the maximum of the numbers chosen
  (!) test run
  (2,3 7) to just do twos, threes, and sevens
  (SCORES) to list all the scores
""")
            type = next(filter(lambda x: x['name'] == name, reversed(config['sessions'])), None)
            if type == None:
                type = ''
            else:
                type = type['type']
            t = input("What would you like to practice? Enter one or more letters [{0}]: ".format(type))
            if t == '':
                t = type
            type = t.upper()
            ops = type

            if ops == 'SCORES':
                scores()
                continue

            matches = re.findall(r"\d+", ops)
            if matches != []:
                numbers = [int(x) for x in matches]
            if "!" in ops:
                test = True
            if "*" in ops:
                ops = ops.replace("*","ASMDF")
            if "@" in ops:
                onlymax = True
            loop = False

            ops= re.sub("[^ASMDFN/]", "", ops)
            for op in ops:
                if op == "N":
                    negatives = True
                    ops = ops.replace("N","")
                    continue
                if not op in ["A","S","M","D","F","/"]:
                    loop = True
                    break
                
        now = datetime.datetime.today().strftime("%Y%m%d%H%M%S")
        if ops != '':
            # New session
            session = {'name': name, 'score': 0, 'right': 0, 'wrong': 0, 'type': type, 'when': now}
            main()
        end = time.time()
        secs = end - start

        # Save scores
        if test or name == "Anonymous" or session['score'] <= 0:
            print("\nScores not saved for anonymous")
        else:
            config["sessions"].append(session)
            # Write to MathQuiz.sessions_
            with open(CONFIG_FILENAME + '_', 'w') as f:
                json.dump(config, f, indent=4, sort_keys=True)
            # Move MathQuiz.sessions to MathQuiz_YYYYMMDDHHmmSS.sessions
            os.rename(CONFIG_FILENAME, CONFIG_FILENAME + '_' + now)
            # Move MathQuiz.sessions_ to MathQuiz.sessions
            os.rename(CONFIG_FILENAME + '_', CONFIG_FILENAME)

        guesses = session['right'] + session['wrong']

        score = session['score']
        money = score / 1000.0
        print("""
    
    Your score was {0} for {1} guesses.
    You took {2:.2f} seconds, which averages {3:.2f} seconds per guess.
    You win ${4:,.2f}

    Try again? (Y)es, (N)o: 
    """.format(score, guesses, secs, secs / guesses if guesses > 0 else secs, money))

        q = input().strip().upper()
        if q == "N":
            break
