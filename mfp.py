import myfitnesspal
import stdiomask

def signin():
    # Attempt to login with user password
    try:
        client = myfitnesspal.Client('geoffreybowles3', password=stdiomask.getpass())
        return client
    except:
        print("Wrong password or username. Please try again.")

def get_meals():
    client = signin()

    day = client.get_date(2022, 1, 27)
    for i in range(4):
        meal = day.meals[i]
        entries = meal.entries
        print(entries)
    print(f"Total {day.totals}")
    
get_meals()