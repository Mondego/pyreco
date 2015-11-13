__FILENAME__ = lesson05_apis
# Knowledge Sharing from Lesson 5: APIs

print len(response)

if response == []:
    print "Sorry not found"

if title[0:3] == 'The':
    title = title.replace("The", "")

if title.isdigits():
    print "It's all digits!"

# Getting KeyErrors? use .get()

if response.get('title'):
    print "There's a title here"

# Don't do too much at once!
# Break it down step by step.

# Be sure to use the right endpoint and parameters

# Getting user input to attach as a parameter
title = raw_input("What movie do you want? ")

url = 'http://bechdeltest.com/api/v1/getMoviesByTitle?title={0}'.format(title).replace(" ","+").replace("'","&#39;")

print url

response = requests.get(url).json()

# Formatting of an IMDB ID vs. a title

# Having lots of users makes testing great

# Use multiple raw_inputs if it didn't find the movie!

# Sometimes the endpoints return different responses!

# Removing spaces from the user input
title = title.strip()

# Removing 'The' from the user input ... any of these characters
title = title.strip('The')

if title[0:4] == 'The ':
    title = title[4:]

# ASCII replaces: www.asciitables.com
import urllib
url = urllib.quote(url)

response = requests.get(url)

# Using .get() to avoid KeyErrors
# Using .get('key', 'ifnotfound')

# Converting the responses to the format we needed

# Using multiple APIs: sometimes the parameters need adjustment

# Thelma and Louise? Don't remove the 'The'

# Loop through and test -- you can't fix every user error

# Mash on your keyboard for user testing

title = 'lsdfasdjflksjflksd'

# Don't forget .json()

########NEW FILE########
__FILENAME__ = lesson01_pbj
# Peanut Butter Jelly Time!

# First Goal: Create a program that can tell you whether or not you can make a peanut butter and jelly sandwich

# Second Goal: Modify that program to tell you: if you can make a sandwich, how many you can make

# Third Goal: Modify that program to allow you to make open-face sandwiches if you have an odd number of slices of bread ( )

# Fourth Goal: Modify that program to tell you: if you're missing ingredients, which ones you need to be able to make your sandwiches

# Fifth Goal: Modify that program to tell you: if you have enough bread and peanut butter but no jelly, that you can make a peanut butter sandwich but you should take a hard, honest look at your life.  Wow, your program is kinda judgy.


# What are the step-by-steps to recreate this?
# First, you need variables to store your information.  Remember, variables are just containers for your information that you give a name.

# You need three ingredients to make a PB&J, so you'll want three different variables:
# 		How much bread do you have? (make this a number that reflects how many slices of bread you have)
#		How much peanut butter do you have? (make this a number that reflects how many sandwiches-worth of peanut butter you have)
#		How much jelly do you have? (make this a number that reflects how many sandwiches-worth of jelly you have)

# For this exercise, we'll assume you have the requisite tools (plate, knife, etc)

# Once you've defined your variables that tell you how much of each ingredient you have, use conditionals to test whether you have the right amount of ingredients

# Based on the results of that conditional, display a message.

# To satisfy the first goal:
#		If you have enough bread (2 slices), peanut butter (1), and jelly (1), print a message like "I can make a peanut butter and jelly sandwich"; 
#		If you don't; print a message like "Looks like I don't have a lunch today"

# To satisfy the second goal:
#		Continue from the first goal, and add:
#		If you have enough bread (at least 2 slices), peanut butter (at least 1), and jelly (at least 1), print a message like "I can make this many sandwiches: " and then calculate the result.
#		If you don't; you can print the same message as before

# To satisfy the third goal:
#		Continue from the second goal, and add:
#		If you have an odd number of slices of bread* and odd amount of peanut butter and jelly, print a message like before, but mention that you can make an open-face sandwich, too.
#		If you don't have enough ingredients; still print the same message as before
#		* To calculate whether you have an odd number, see https://github.com/shannonturner/python-lessons/blob/master/section_01_(basics)/simple_math.py

# To satisfy the fourth goal:
#		Continue from the third goal, but this time if you don't have enough ingredients, print a message that tells you which ones you're missing.

# To satisfy the fifth goal:
#		Continue from the fourth goal, but this time if you have enough bread and peanut butter but no jelly, print a message that tells you that you can make a peanut butter sandwich
#		Or if you have more peanut butter and bread than jelly, that you can make a certain number of peanut butter & jelly sandwiches and a certain number of peanut butter sandwiches


########NEW FILE########
__FILENAME__ = lesson02_99bottles
# Can you make Python print out the song for 99 bottles of beer on the wall?

# Note: You can use range() in three different ways

# First:
# range(5) will give you a list containing [0, 1, 2, 3, 4]
# In this case, range assumes you want to start counting at 0, and the parameter you give is the number to stop *just* short of.

# Second:
# range(5, 10) will give you a list containing [5, 6, 7, 8, 9]
# In this case, the two parameters you give to range() are the number to start at and the number to stop *just* short of.
# Helpful mnemonic: range(start, stop)

# Third:
# range(5, 15, 3) will give you a list containing [5, 8, 11, 14]
# In this case, the three parameters you give to range() are the number to start at, the number to stop *just* short of, and the number to increment each time by.
# Note that normally, the number to increment each time by is assumed to be 1.  (In other words, you add 1 each time through.)
# That's why it goes [0, 1, 2, 3, 4] unless you specify that third parameter, called the step.
# Helpful mnemonic: range(start, stop, step)

# Using range() and a loop, print out the song.  Your output should look like this:

# 99 bottles of beer on the wall, 99 bottles of beer ...
# If one of those bottles should happen to fall, 98 bottles of beer on the wall
# 98 bottles of beer on the wall, 98 bottles of beer ...
# If one of those bottles should happen to fall, 97 bottles of beer on the wall
# 97 bottles of beer on the wall, 97 bottles of beer ...
# If one of those bottles should happen to fall, 96 bottles of beer on the wall
# 96 bottles of beer on the wall, 96 bottles of beer ...
# If one of those bottles should happen to fall, 95 bottles of beer on the wall
# 95 bottles of beer on the wall, 95 bottles of beer ...
# If one of those bottles should happen to fall, 94 bottles of beer on the wall
# 94 bottles of beer on the wall, 94 bottles of beer ...
# If one of those bottles should happen to fall, 93 bottles of beer on the wall
# 93 bottles of beer on the wall, 93 bottles of beer ...
# If one of those bottles should happen to fall, 92 bottles of beer on the wall
# 92 bottles of beer on the wall, 92 bottles of beer ...
# If one of those bottles should happen to fall, 91 bottles of beer on the wall
# 91 bottles of beer on the wall, 91 bottles of beer ...
# If one of those bottles should happen to fall, 90 bottles of beer on the wall
# 90 bottles of beer on the wall, 90 bottles of beer ...
# If one of those bottles should happen to fall, 89 bottles of beer on the wall
# 89 bottles of beer on the wall, 89 bottles of beer ...
# If one of those bottles should happen to fall, 88 bottles of beer on the wall
# 88 bottles of beer on the wall, 88 bottles of beer ...
# If one of those bottles should happen to fall, 87 bottles of beer on the wall
# 87 bottles of beer on the wall, 87 bottles of beer ...
# If one of those bottles should happen to fall, 86 bottles of beer on the wall
# 86 bottles of beer on the wall, 86 bottles of beer ...
# If one of those bottles should happen to fall, 85 bottles of beer on the wall
# 85 bottles of beer on the wall, 85 bottles of beer ...
# If one of those bottles should happen to fall, 84 bottles of beer on the wall
# 84 bottles of beer on the wall, 84 bottles of beer ...
# If one of those bottles should happen to fall, 83 bottles of beer on the wall
# 83 bottles of beer on the wall, 83 bottles of beer ...
# If one of those bottles should happen to fall, 82 bottles of beer on the wall
# 82 bottles of beer on the wall, 82 bottles of beer ...
# If one of those bottles should happen to fall, 81 bottles of beer on the wall
# 81 bottles of beer on the wall, 81 bottles of beer ...
# If one of those bottles should happen to fall, 80 bottles of beer on the wall
# 80 bottles of beer on the wall, 80 bottles of beer ...
# If one of those bottles should happen to fall, 79 bottles of beer on the wall
# 79 bottles of beer on the wall, 79 bottles of beer ...
# If one of those bottles should happen to fall, 78 bottles of beer on the wall
# 78 bottles of beer on the wall, 78 bottles of beer ...
# If one of those bottles should happen to fall, 77 bottles of beer on the wall
# 77 bottles of beer on the wall, 77 bottles of beer ...
# If one of those bottles should happen to fall, 76 bottles of beer on the wall
# 76 bottles of beer on the wall, 76 bottles of beer ...
# If one of those bottles should happen to fall, 75 bottles of beer on the wall
# 75 bottles of beer on the wall, 75 bottles of beer ...
# If one of those bottles should happen to fall, 74 bottles of beer on the wall
# 74 bottles of beer on the wall, 74 bottles of beer ...
# If one of those bottles should happen to fall, 73 bottles of beer on the wall
# 73 bottles of beer on the wall, 73 bottles of beer ...
# If one of those bottles should happen to fall, 72 bottles of beer on the wall
# 72 bottles of beer on the wall, 72 bottles of beer ...
# If one of those bottles should happen to fall, 71 bottles of beer on the wall
# 71 bottles of beer on the wall, 71 bottles of beer ...
# If one of those bottles should happen to fall, 70 bottles of beer on the wall
# 70 bottles of beer on the wall, 70 bottles of beer ...
# If one of those bottles should happen to fall, 69 bottles of beer on the wall
# 69 bottles of beer on the wall, 69 bottles of beer ...
# If one of those bottles should happen to fall, 68 bottles of beer on the wall
# 68 bottles of beer on the wall, 68 bottles of beer ...
# If one of those bottles should happen to fall, 67 bottles of beer on the wall
# 67 bottles of beer on the wall, 67 bottles of beer ...
# If one of those bottles should happen to fall, 66 bottles of beer on the wall
# 66 bottles of beer on the wall, 66 bottles of beer ...
# If one of those bottles should happen to fall, 65 bottles of beer on the wall
# 65 bottles of beer on the wall, 65 bottles of beer ...
# If one of those bottles should happen to fall, 64 bottles of beer on the wall
# 64 bottles of beer on the wall, 64 bottles of beer ...
# If one of those bottles should happen to fall, 63 bottles of beer on the wall
# 63 bottles of beer on the wall, 63 bottles of beer ...
# If one of those bottles should happen to fall, 62 bottles of beer on the wall
# 62 bottles of beer on the wall, 62 bottles of beer ...
# If one of those bottles should happen to fall, 61 bottles of beer on the wall
# 61 bottles of beer on the wall, 61 bottles of beer ...
# If one of those bottles should happen to fall, 60 bottles of beer on the wall
# 60 bottles of beer on the wall, 60 bottles of beer ...
# If one of those bottles should happen to fall, 59 bottles of beer on the wall
# 59 bottles of beer on the wall, 59 bottles of beer ...
# If one of those bottles should happen to fall, 58 bottles of beer on the wall
# 58 bottles of beer on the wall, 58 bottles of beer ...
# If one of those bottles should happen to fall, 57 bottles of beer on the wall
# 57 bottles of beer on the wall, 57 bottles of beer ...
# If one of those bottles should happen to fall, 56 bottles of beer on the wall
# 56 bottles of beer on the wall, 56 bottles of beer ...
# If one of those bottles should happen to fall, 55 bottles of beer on the wall
# 55 bottles of beer on the wall, 55 bottles of beer ...
# If one of those bottles should happen to fall, 54 bottles of beer on the wall
# 54 bottles of beer on the wall, 54 bottles of beer ...
# If one of those bottles should happen to fall, 53 bottles of beer on the wall
# 53 bottles of beer on the wall, 53 bottles of beer ...
# If one of those bottles should happen to fall, 52 bottles of beer on the wall
# 52 bottles of beer on the wall, 52 bottles of beer ...
# If one of those bottles should happen to fall, 51 bottles of beer on the wall
# 51 bottles of beer on the wall, 51 bottles of beer ...
# If one of those bottles should happen to fall, 50 bottles of beer on the wall
# 50 bottles of beer on the wall, 50 bottles of beer ...
# If one of those bottles should happen to fall, 49 bottles of beer on the wall
# 49 bottles of beer on the wall, 49 bottles of beer ...
# If one of those bottles should happen to fall, 48 bottles of beer on the wall
# 48 bottles of beer on the wall, 48 bottles of beer ...
# If one of those bottles should happen to fall, 47 bottles of beer on the wall
# 47 bottles of beer on the wall, 47 bottles of beer ...
# If one of those bottles should happen to fall, 46 bottles of beer on the wall
# 46 bottles of beer on the wall, 46 bottles of beer ...
# If one of those bottles should happen to fall, 45 bottles of beer on the wall
# 45 bottles of beer on the wall, 45 bottles of beer ...
# If one of those bottles should happen to fall, 44 bottles of beer on the wall
# 44 bottles of beer on the wall, 44 bottles of beer ...
# If one of those bottles should happen to fall, 43 bottles of beer on the wall
# 43 bottles of beer on the wall, 43 bottles of beer ...
# If one of those bottles should happen to fall, 42 bottles of beer on the wall
# 42 bottles of beer on the wall, 42 bottles of beer ...
# If one of those bottles should happen to fall, 41 bottles of beer on the wall
# 41 bottles of beer on the wall, 41 bottles of beer ...
# If one of those bottles should happen to fall, 40 bottles of beer on the wall
# 40 bottles of beer on the wall, 40 bottles of beer ...
# If one of those bottles should happen to fall, 39 bottles of beer on the wall
# 39 bottles of beer on the wall, 39 bottles of beer ...
# If one of those bottles should happen to fall, 38 bottles of beer on the wall
# 38 bottles of beer on the wall, 38 bottles of beer ...
# If one of those bottles should happen to fall, 37 bottles of beer on the wall
# 37 bottles of beer on the wall, 37 bottles of beer ...
# If one of those bottles should happen to fall, 36 bottles of beer on the wall
# 36 bottles of beer on the wall, 36 bottles of beer ...
# If one of those bottles should happen to fall, 35 bottles of beer on the wall
# 35 bottles of beer on the wall, 35 bottles of beer ...
# If one of those bottles should happen to fall, 34 bottles of beer on the wall
# 34 bottles of beer on the wall, 34 bottles of beer ...
# If one of those bottles should happen to fall, 33 bottles of beer on the wall
# 33 bottles of beer on the wall, 33 bottles of beer ...
# If one of those bottles should happen to fall, 32 bottles of beer on the wall
# 32 bottles of beer on the wall, 32 bottles of beer ...
# If one of those bottles should happen to fall, 31 bottles of beer on the wall
# 31 bottles of beer on the wall, 31 bottles of beer ...
# If one of those bottles should happen to fall, 30 bottles of beer on the wall
# 30 bottles of beer on the wall, 30 bottles of beer ...
# If one of those bottles should happen to fall, 29 bottles of beer on the wall
# 29 bottles of beer on the wall, 29 bottles of beer ...
# If one of those bottles should happen to fall, 28 bottles of beer on the wall
# 28 bottles of beer on the wall, 28 bottles of beer ...
# If one of those bottles should happen to fall, 27 bottles of beer on the wall
# 27 bottles of beer on the wall, 27 bottles of beer ...
# If one of those bottles should happen to fall, 26 bottles of beer on the wall
# 26 bottles of beer on the wall, 26 bottles of beer ...
# If one of those bottles should happen to fall, 25 bottles of beer on the wall
# 25 bottles of beer on the wall, 25 bottles of beer ...
# If one of those bottles should happen to fall, 24 bottles of beer on the wall
# 24 bottles of beer on the wall, 24 bottles of beer ...
# If one of those bottles should happen to fall, 23 bottles of beer on the wall
# 23 bottles of beer on the wall, 23 bottles of beer ...
# If one of those bottles should happen to fall, 22 bottles of beer on the wall
# 22 bottles of beer on the wall, 22 bottles of beer ...
# If one of those bottles should happen to fall, 21 bottles of beer on the wall
# 21 bottles of beer on the wall, 21 bottles of beer ...
# If one of those bottles should happen to fall, 20 bottles of beer on the wall
# 20 bottles of beer on the wall, 20 bottles of beer ...
# If one of those bottles should happen to fall, 19 bottles of beer on the wall
# 19 bottles of beer on the wall, 19 bottles of beer ...
# If one of those bottles should happen to fall, 18 bottles of beer on the wall
# 18 bottles of beer on the wall, 18 bottles of beer ...
# If one of those bottles should happen to fall, 17 bottles of beer on the wall
# 17 bottles of beer on the wall, 17 bottles of beer ...
# If one of those bottles should happen to fall, 16 bottles of beer on the wall
# 16 bottles of beer on the wall, 16 bottles of beer ...
# If one of those bottles should happen to fall, 15 bottles of beer on the wall
# 15 bottles of beer on the wall, 15 bottles of beer ...
# If one of those bottles should happen to fall, 14 bottles of beer on the wall
# 14 bottles of beer on the wall, 14 bottles of beer ...
# If one of those bottles should happen to fall, 13 bottles of beer on the wall
# 13 bottles of beer on the wall, 13 bottles of beer ...
# If one of those bottles should happen to fall, 12 bottles of beer on the wall
# 12 bottles of beer on the wall, 12 bottles of beer ...
# If one of those bottles should happen to fall, 11 bottles of beer on the wall
# 11 bottles of beer on the wall, 11 bottles of beer ...
# If one of those bottles should happen to fall, 10 bottles of beer on the wall
# 10 bottles of beer on the wall, 10 bottles of beer ...
# If one of those bottles should happen to fall, 9 bottles of beer on the wall
# 9 bottles of beer on the wall, 9 bottles of beer ...
# If one of those bottles should happen to fall, 8 bottles of beer on the wall
# 8 bottles of beer on the wall, 8 bottles of beer ...
# If one of those bottles should happen to fall, 7 bottles of beer on the wall
# 7 bottles of beer on the wall, 7 bottles of beer ...
# If one of those bottles should happen to fall, 6 bottles of beer on the wall
# 6 bottles of beer on the wall, 6 bottles of beer ...
# If one of those bottles should happen to fall, 5 bottles of beer on the wall
# 5 bottles of beer on the wall, 5 bottles of beer ...
# If one of those bottles should happen to fall, 4 bottles of beer on the wall
# 4 bottles of beer on the wall, 4 bottles of beer ...
# If one of those bottles should happen to fall, 3 bottles of beer on the wall
# 3 bottles of beer on the wall, 3 bottles of beer ...
# If one of those bottles should happen to fall, 2 bottles of beer on the wall
# 2 bottles of beer on the wall, 2 bottles of beer ...
# If one of those bottles should happen to fall, 1 bottles of beer on the wall
########NEW FILE########
__FILENAME__ = lesson02_movies
# Goal #1: Create a program that will print out a list of movie titles and a set of ratings defined below into a particular format.

# First, choose any five movies you want.

# Next, look each movie up manually to find out four pieces of information:
#		Their parental guidance rating (G, PG, PG-13, R)
#		Their Bechdel Test Rating (See http://shannonvturner.com/bechdel or http://bechdeltest.com/)
#		Their IMDB Rating from 0 - 10 (See http://imdb.com/)
# 		Their genre according to IMDB

# After a few more lessons, you'll be able to tell Python to go out and get that information for you, but for now you'll have to collect it on your own.

# Now that you've written down each piece of information for all five of your movies, save them into variables.

# You'll need a variable for movie_titles, a variable for parental_rating, a variable for bechdel_rating, a variable for imdb_rating, and a variable for genre.

# Since you have five sets of facts about five movies, you'll want to use lists to hold these pieces of information.

# Once all of your information is stored in lists, loop through those lists to print out information with each part separated by a comma, like this:

# Example:
# Jurassic Park, PG-13, 3, 8.0, Adventure / Sci-Fi
# Back to the Future, PG, 1, 8.5, Adventure / Comedy / Sci-Fi

# Note how each piece of information is separated by a comma.  This is a specific file format called the "Comma Separated Value (CSV)" format
# If you can make a CSV file, you can open it up in Excel or Numbers as a spreadsheet.

# When you've printed out your information like the example above, copy/paste that into a file and save it as a .csv file.
# Open that up in Excel, Numbers, or another spreadsheet program.  How does it look?
# To see an example of how it should look, check out: https://github.com/shannonturner/python-lessons/blob/master/section_05_(loops)/movies.csv
########NEW FILE########
__FILENAME__ = lesson02_pbj_while
# Goal #1: Write a new version of the PB&J program that uses a while loop.  Print "Making sandwich #" and the number of the sandwich until you are out of bread, peanut butter, or jelly.

# Example:
# bread = 4
# peanut_butter = 3
# jelly = 10

# Output:
# Making sandwich #1
# Making sandwich #2
# All done; only had enough bread for 2 sandwiches.

# Goal #2: Modify that program to say how many sandwiches-worth of each ingredient remains.

# Example 2:
# bread = 10
# peanut_butter = 10
# jelly = 4

# Output:
# Making sandwich #1
# I have enough bread for 4 more sandwiches, enough peanut butter for 9 more, and enough jelly for 3 more.
# Making sandwich #2
# I have enough bread for 3 more sandwiches, enough peanut butter for 8 more, and enough jelly for 2 more.
# Making sandwich #3
# I have enough bread for 2 more sandwiches, enough peanut butter for 7 more, and enough jelly for 1 more.
# Making sandwich #4
# All done; I ran out of jelly.
########NEW FILE########
__FILENAME__ = lesson02_states
# Goal: Create a program that prints out an HTML drop down menu for all 50 states

# Step 1: Define your list of states
# These should all be strings, since they're names of places
# Instead of having to type them all out, I really like liststates.com -- you can even customize the format it gives you the states in to make it super easy to copy/paste into your code here

# Step 2: Create your loop
# Essentially, you're telling Python: for each state in my list: print this HTML code
# A good place to start is by printing the name of the state in the loop; after that you can add the HTML around it

# Step 3: Add the HTML
# A drop-down menu in HTML looks like this:

# <select>
# 			<option value="state_abbreviation">Full state name</option>
# </select>

# At line 14, we create the drop-down menu
# At line 15, we create one drop-down item.  Each additional <option> that we add will add another item to our drop-down menu
# At line 16, we tell HTML that we're done with the drop-down menu

# Step 4: Test it!
# Have Python print out the HTML code. Copy / paste it into a file, save that file as "states.html" and open that file in a web browser.
# Later, when we learn file handling, we can skip the copy/paste step.
# File handling can also let us create a file with the state names and abbreviations in it so we don't have to add it to our code.

# Your finished project should look something like: https://github.com/shannonturner/python-lessons/blob/master/section_05_(loops)/states.html
########NEW FILE########
__FILENAME__ = lesson03_compare
# Challenge Level: Advanced

# NOTE: Please don't use anyone's *real* contact information during these exercises, especially if you're putting it up on Github!

# Background: You took a survey of all of the employees at your organization to see what their twitter and github names were. You got a few responses.
#   You have two spreadsheets in CSV (comma separated value) format:
#       all_employees.csv: See section_07_(files).  Contains all of the employees in your organization and their contact info.
#           Columns: name, email, phone, department, position
#       survey.csv: See section_07_(files).  Contains info for employees who have completed a survey.  Not all employees have completed the survey.
#           Columns: email, twitter, github

# Challenge 1: Open all_employees.csv and survey.csv and compare the two.  When an employee from survey.csv appears in all_employees.csv, print out the rest of their information from all_employees.csv.

# Sample output:
#       Shannon Turner took the survey! Here is her contact information: Twitter: @svt827 Github: @shannonturner Phone: 202-555-1234

# Challenge 2: Add the extra information from survey.csv into all_employees.csv as extra columns.  
# IMPORTANT: It would probably be a good idea to save it as an extra file instead of accidentally overwriting your original!
# By the end, your all_employees.csv should contain the following columns: name, email, phone, department, position, twitter, github
########NEW FILE########
__FILENAME__ = lesson03_contacts
# Challenge Level: Beginner

# NOTE: Please don't use anyone's *real* contact information during these exercises, especially if you're putting it up on Github!

# Background: You have a dictionary with people's contact information.  You want to display that information as an HTML table.

contacts = {
    'Shannon': {'phone': '202-555-1234', 'twitter': '@svt827', 'github': '@shannonturner' }, 
    'Beyonce': {'phone': '303-404-9876', 'twitter': '@beyonce', 'github': '@bey'},
    'Tegan and Sara': {'phone': '301-777-3313', 'twitter': '@teganandsara', 'github': '@heartthrob'}
}

# Goal 1: Loop through that dictionary to print out everyone's contact information.

# Sample output:

# Shannon's contact information is:
#   Phone: 202-555-1234
#   Twitter: @svt827
#   Github: @shannonturner 

# Beyonce's contact information is:
#   Phone: 303-404-9876
#   Twitter: @beyonce
#   Github: @bey


# Goal 2:  Display that information as an HTML table.

# Sample output:

# <table border="1">
# <tr>
# <td colspan="2"> Shannon </td>
# </tr>
# <tr>
# <td> Phone: 202-555-1234 </td>
# <td> Twitter: @svt827 </td>
# <td> Github: @shannonturner </td>
# </tr>
# </table>

# ...

# Goal 3: Write all of the HTML out to a file called contacts.html and open it in your browser.

# Goal 4: Instead of reading in the contacts from the dictionary above, read them in from contacts.csv, which you can find in lesson_07_(files).
########NEW FILE########
__FILENAME__ = lesson03_states
# Challenge Level: Beginner

# Background: You have a text file with all of the US state names:
#       states.txt: See section_07_(files).  
#
#       You also have a spreadsheet in comma separated value (CSV) format, state_info.csv.  See also section_07_(files)
#       state_info.csv has the following columns: Population Rank, State Name, Population, US House Members, Percent of US Population

# Challenge 1: Open states.txt and use the information to generate an HTML drop-down menu as in: https://github.com/shannonturner/python-lessons/blob/master/playtime/lesson02_states.py

# Challenge 2: Save the HTML as states.html instead of printing it to screen.  
# Your states.html should look identical (or at least similar) to the one you created in the Lesson 2 playtime, except you're getting the states from a file instead of a list.

# Challenge 3: Using state_info.csv, create an HTML page that has a table for *each* state with all of the state details.

# Sample output:

# <table border="1">
# <tr>
# <td colspan="2"> California </td>
# </tr>
# <tr>
# <td> Rank: 1 </td>
# <td> Percent: 11.91% </td>
# </tr>
# <tr>
# <td> US House Members: 53 </td>
# <td> Population: 38,332,521 </td>
# </tr>
# </table>

# Challenge 4 (Not a Python challenge, but an HTML/Javascript challenge): When you make a choice from the drop-down menu, jump to that state's table.
########NEW FILE########
__FILENAME__ = lesson04_csvtolist
# Challenge level: Beginner

# Goal: Using the code from Lesson 3: File handling and dictionaries, create a function that will open a CSV file and return the result as a nested list.
########NEW FILE########
__FILENAME__ = lesson04_deduplicate
# Challenge level: Beginner

# Scenario: You have two files containing a list of email addresses of people who attended your events.
#       File 1: People who attended your Film Screening event
#       https://github.com/shannonturner/python-lessons/blob/master/section_09_(functions)/film_screening_attendees.txt
#
#       File 2: People who attended your Happy hour
#       https://github.com/shannonturner/python-lessons/blob/master/section_09_(functions)/happy_hour_attendees.txt
#

# Note: You should create functions to accomplish your goals.

# Goal 1: You want to get a de-duplicated list of all of the people who have come to your events.

# Goal 2: Who came to *both* your Film Screening and your Happy hour?

########NEW FILE########
__FILENAME__ = lesson04_group_csvtodict
# Challenge Level: Advanced

# Group exercise!

# Scenario: Your organization has put on three events and you have a CSV with details about those events
#           You have the event's date, a brief description, its location, how many attended, how much it cost, and some brief notes
#           File: https://github.com/shannonturner/python-lessons/blob/master/section_09_(functions)/events.csv

# Goal: Read this CSV into a dictionary.

# Your function should return a dictionary that looks something like this. 
# Bear in mind dictionaries have no order, so yours might look a little different!
# Note that I 'faked' the order of my dictionary by using the row numbers as my keys.

# {0: 
#     {'attendees': '12', 
#     'description': 'Film Screening', 
#     'notes': 'Panel afterwards', 
#     'cost': '$10 suggested', 
#     'location': 'In-office', 
#     'date': '1/11/2014'}, 

# 1: 
#     {'attendees': '12', 
#     'description': 'Happy Hour', 
#     'notes': 'Too loud', 
#     'cost': '0', 
#     'location': 'That bar with the drinks', 
#     'date': '2/22/2014'}, 
# 2: 
#     {'attendees': '200', 
#     'description': 'Panel Discussion', 
#     'notes': 'Full capacity and 30 on waitlist', 
#     'cost': '0', 
#     'location': 'Partner Organization', 
#     'date': '3/31/2014'}
# }
########NEW FILE########
__FILENAME__ = lesson05_firstapi
# Exercise: Using your first API

# API documentation: http://bechdeltest.com/api/v1/doc

# Goal 1:
#   Ask the user for the movie title they want to check
#   Display all of the details about the movie returned by the API
#
#   Things to keep in mind:
#       How will your program behave when multiple movies are returned?
#       How will your program behave when no movies are returned?
#       How will your program behave with works like "the" in the title?

# Goal 2:
#   Check to see if the user input is a movie title or an ImdbID and use the proper endpoint

# Goal 3:
# Integrate this with the Open Movie Database API: http://www.omdbapi.com/
#   Display all of the details from both APIs when searching for a movie.
#   Note that you may need to prefix your ImdbIDs with 'tt' to get the search to work.

# Copy these URLs into your browser!
# To visualize as a CSV, copy the JSON into http://konklone.io/json

# Sample Bechdel test API returns: http://bechdeltest.com/api/v1/getMovieByImdbId?imdbid=0367631
# JSON: 
    # {
    #   "visible": "1",
    #   "date": "2009-12-05 05:13:37",
    #   "submitterid": "270",
    #   "rating": "3",
    #   "dubious": "0",
    #   "imdbid": "0367631",
    #   "id": "551",
    #   "title": "D.E.B.S.",
    #   "year": "2004"
    # }
# JSON to CSV link: http://konklone.io/json/?id=11488879

# Sample Open Movie Database API returns: http://www.omdbapi.com/?i=tt0367631&t=
# JSON:
    # {
    #   "Title": "D.E.B.S.",
    #   "Year": "2004",
    #   "Rated": "PG-13",
    #   "Released": "25 Mar 2005",
    #   "Runtime": "91 min",
    #   "Genre": "Action, Comedy, Romance",
    #   "Director": "Angela Robinson",
    #   "Writer": "Angela Robinson",
    #   "Actors": "Sara Foster, Jordana Brewster, Meagan Good, Devon Aoki",
    #   "Plot": "Plaid-skirted schoolgirls are groomed by a secret government agency to become the newest members of the elite national-defense group, D.E.B.S.",
    #   "Language": "English",
    #   "Country": "USA",
    #   "Awards": "1 win & 2 nominations.",
    #   "Poster": "http://ia.media-imdb.com/images/M/MV5BMjA0OTU5ODgyOF5BMl5BanBnXkFtZTcwODczNDgyMQ@@._V1_SX300.jpg",
    #   "Metascore": "42",
    #   "imdbRating": "5.2",
    #   "imdbVotes": "10,563",
    #   "imdbID": "tt0367631",
    #   "Type": "movie",
    #   "Response": "True"
    # }
# JSON to CSV link: http://konklone.io/json/?id=11488839
########NEW FILE########
__FILENAME__ = basic_syntax

# Basic Syntax

# This is a comment.
# That means Python will let you write notes to yourself and to the other coders checking out your code
# And Python won't run this at all, or even notice it.

# The # symbol is what creates a comment.
# You can have a comment on a line all by itself

# The print statement is a good place to start -- it allows us to see results right away.

print "Or you can have a comment on the same line" # as a command that Python WILL run

print "The print statement will output some text to the screen." # it doesn't print anything to paper.

# Python will run commands from top to bottom, left to right

# So the print statement on line 11 will run before the print statement on line 13




print "You can use lots of newlines to space things out if you like"
print "Or you can keep your statements close to one another."

print "It's really up to you, but generally speaking, you'll want to make your code as readable as possible."

# These two statements are identical
print 4+4
print 4 + 4

# Indentation levels matter a lot, even if other kinds of whitespace like newlines or spacing don't matter as much

# So if you uncommented the next line and ran this, you'd get an error.
#    print 4 + 4

########NEW FILE########
__FILENAME__ = data_types

# Data types: int, float, bool, str

# In Simple Math and Variable Assignment, we saw ints and floats in action.
# Here's a quick refresher.

# ints are whole numbers
print 5 + 2, 5 - 3, 5 * 5, 5 / 2 # 7, 2, 25, 2

# floats are decimal numbers
print 5.4 + 2.1, 5.0 - 3, 5.7 * 5.2, 5 / 2.0 # 7.5, 2.0, 29.64, 2.5

# boolean values store True or False (yes or no)
print 5 > 4 # True
print 3 + 3 <= 1 # False

# Comparison Operators Sneak Peek
#   >    greater than
#   <    less than
#   >=   greater than or equal to
#   <=   less than or equal to
#   !=   not equal to
#   ==   is equal to

# strings are covered in greater detail in Section 2
# But essentially, they contain words, or really, anything you could type on a keyboard
print "Yep, all those print statements you saw before? Those things between the quotes are strings! Yes, I'm a string, too. "

print "Python usually isn't too strict about data types, but there are some things you can't do."

# Uncomment out the next line to get an error!
#print "This line here will cause an error, because you can't add strings to numbers. This is Lesson Section #" + 1


########NEW FILE########
__FILENAME__ = simple_math

# Simple Math

# We're going to work with print statements to output the results to the screen.

# You can separate multiple print items with a comma, as shown below:

print "Four times four is ", 4 * 4

# Addition
print "5 + 3 is ", 5 + 3

# Subtraction
print "6 - 2 is ", 6 - 2

# Multiplication
print "10 * 20 is ", 10 * 20

# Division
print "55 / 2 is ", 55 / 2 # Hmm ... !

print "By default, Python treats numbers as whole numbers (integers)"
print "So in a way, Python's answer of 55 / 2 = 27 makes sense, even if it's not quite what we're looking for."
print "Luckily, there are other ways to get the answer we want."

# Precise Division (using floats)
print "55.0 / 2 is ", 55.0 / 2
print "55 / 2.0 is ", 55 / 2.0
print "55.0 / 2.0 is ", 55.0 / 2.0

# Remainder Division
print "55 % 2 is ", 55 % 2 # This is super useful for determining whether a number is odd or even

# Powers
print "2 ** 10 is ", 2 ** 10

########NEW FILE########
__FILENAME__ = variable_assignment

# Variable assignment

# In Python (or any programming language), variables hold information that you can access, use, and change
# In Python, there are lots of different types of information that you can hold

# Some languages make you decide early on what type of information you want to store, or even what the name of a variable is, before you even get started.
# I like Python because it's flexible and forgiving.


# Rules of variable names
# -----------------------
# Variables must begin with a letter or underscore
# Variables may contain letters and numbers and underscores, but not spaces
# Variables can't be named the same thing as built-in Python commands

# If you see a word on its own that isn't reserved to Python, chances are it's a variable.

lesson_section = 1 # General Programming Basics
lesson_subsection = 2 # Variable Assignment

# In line 19, I'm telling Python I want to create a variable called 'section' and set it equal to 1

# Shannon's Rules of variable names
# ---------------------------------
# Variables should be descriptive, even if it means their names are long
# You should be able to show your code to anyone and they'll know exactly what information a given variable holds
# Use underscores to break up words!

# We've stored values inside of lesson_section and lesson_subsection, so now let's use them!

print "We are on Section #", lesson_section
print "And this is unit #", lesson_subsection, ", which covers Variable Assignment"

print "Take another look at the code for the basic math unit."
print "Anywhere you see a number in that code, you can replace it with a variable that holds a number instead."

# Let's see that in practice:
days_in_a_year = 365 # Beautifully descriptive variable names are their own comments
my_age = 21 # yeah, right!

print "My age is ", my_age, ", and I've been alive for ", days_in_a_year * my_age, " days, give or take."

# Now let's change the value stored in days_in_a_year to account for leap years and try it again.

days_in_a_year = days_in_a_year + .25 # Equivalent to days_in_a_year = 365 + .25

print "My age is ", my_age, ", and I've been alive for ", days_in_a_year * my_age, " days, give or take, now that I'm including leap years."






















########NEW FILE########
__FILENAME__ = is_alphaspace
def is_alphaspace(string):

    """
    Returns True if all characters in the string are spaces or letters; otherwise returns False.

    using str.isalpha() returns a bool on whether ALL of the characters in a string are letters
    using str.isspace() returns a bool on whether ALL of the characters in a string are whitespace;

    Although it's not a string method, this function combines the functionality of the string methods above        
    """
    
    return all([any([char.isspace(), char.isalpha()]) for char in string])

# This custom function will behave similarly to the str.isalpha() and str.isspace() combined together.

test_string = "This string will return false for each of isalpha and isspace but it will return true for the custom function"

print "test_string.isalpha() gives us: ", test_string.isalpha()
print "test_string.isspace() gives us: ", test_string.isspace()

# Note how the syntax differs.  That's because is_alphaspace() isn't a string method, it's a custom function.
print "But is_alphaspace(test_string) gives us: ", is_alphaspace(test_string)


########NEW FILE########
__FILENAME__ = slicing
# Slicing examples
# Slicing allows us to see one piece or 'slice' of an item, like a single character (or set of characters) within a string


# Let's start by creating a variable called github_handle; it will hold a string with my GitHub handle in it
github_handle = '@shannonturner'


# You can use a comma to separate different items that you want to print as shown below
print "My github handle is ", github_handle


# This is our first slicing example.  Notice the square brackets attached directly to the variable name with no spaces in between.
# The two numbers in the middle, separated by a colon, are called the slicing indexes
print "My first name is ", github_handle[1:8]


# Here's how you can visualize the print statement above.

#       @shannonturner
#       0123456789....

# A note about the above: Python starts counting at zero, and the last few letters (r, n, e, r) are tied to 10, 11, 12, 13

# Or, shown vertically, it looks like this:

##      0		@
##      1		s
##      2		h
##      3		a
##      4		n
##      5		n
##      6		o
##      7		n
##      8		t
##      9		u
##      10		r
##      11		n
##      12		e
##      13		r

# So in the example of github_handle[1:8], notice that the t (at slice #8) is not included, but the s (at slice #1), is.
# That's because the first slice value is inclusive, but the second slice value is exclusive.
# I think of it as: Python starts at 1 and walks UNTIL it gets to 8 and then stops, gathering up everything in between.


print "My last name is ", github_handle[8:14]

# Notice that there is no index 14.  If the second index is higher than what exists, Python will assume you mean "until the very end"

# You can omit the second index; Python understands this as "go to the end"
print "My last name is ", github_handle[8:]

# And if you omit the first index, Python understands this as "start from the beginning"
print "My twitter handle is NOT ", github_handle[:8]

# What happens if you use a negative slicing index?

# You can use negative slicing indexes to count backwards from the end, like this:

##      -14		@
##      -13		s
##      -12		h
##      -11		a
##      -10		n
##      -9		n
##      -8		o
##      -7		n
##      -6		t
##      -5		u
##      -4		r
##      -3		n
##      -2		e
##      -1		r

print "My last name is ", github_handle[-6:]

# You can also mix and match positive and negative slicing indexes as needed

print "My first name is ", github_handle[1:-6]

# In these examples, we're relying on knowing the exact slicing indexes.  But what if our string changes in size or content?
# With short strings, it's fairly easy (especially if you write it out as above) to figure out which slices you need.

# But a more common and practical way to slice, rather than using numbers directly, is to create a variable that holds the number you need (but can change as needed)

# If this part is confusing, you may want to revisit this section when you're comfortable with string methods like str.find()

print "### Part Two ###"

text = "My GitHub handle is @shannonturner and my Twitter handle is @svt827"

# Let's extract the GitHub handle using str.find() and slicing.

snail_index = text.find('@')

print text[snail_index:snail_index + 14] # So the first slicing index is given by the variable, but we're still relying on knowing the exact number of characters (14).  We can improve this.

space_after_first_snail_index = text[snail_index:].find(' ') # Note that we're using slicing here to say start the .find() after the first snail is found.

print text[snail_index:snail_index + space_after_first_snail_index] # Why do we need to add snail_index to the second slicing index? Take a look:

print "snail_index is: ", snail_index
print "space_after_first_snail_index is: ", space_after_first_snail_index

print "So this is essentially saying text[20:34], see? --> ", text[20:34]

# Instead of creating a separate variable, you can just add the str.find() that gives the number you want right into the slice, like this:

print text[text.find('@'):text.find('@')+text[text.find('@'):].find(' ')] # But as you can see, it's not the most readable, especially compared to above.

# Still, it's a fairly common syntax / notation, so it's worth being familiar with it and knowing what it looks like in case you run into it.

print "Can you use slicing and string methods like str.find() to extract the Twitter handle from text?"




########NEW FILE########
__FILENAME__ = string_count
# String methods: string.count()

# string.count() tells you how many times one string appears in a larger string

gettysburg_address = """
Four score and seven years ago our fathers brought forth on this continent a new nation, conceived in liberty, and dedicated to the proposition that all men are created equal.
Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. 
We are met on a great battlefield of that war. 
We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live. 
It is altogether fitting and proper that we should do this.
But, in a larger sense, we can not dedicate, we can not consecrate, we can not hallow this ground. 
The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract. 
The world will little note, nor long remember what we say here, but it can never forget what they did here. 
It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced. 
It is rather for us to be here dedicated to the great task remaining before us -- that from these honored dead we take increased devotion to that cause 
for which they gave the last full measure of devotion -- that we here highly resolve that these dead shall not have died in vain -- that this nation, under God, 
shall have a new birth of freedom -- and that government of the people, by the people, for the people, shall not perish from the earth.
"""

# Now that we have a fairly long string to search through, let's see how many times the word "people" appears in the text
print gettysburg_address.count("people") # appears 3 times

# What goes inside the parentheses is the string that you're looking for; the larger string to look inside is the string that comes before the dot.

print gettysburg_address.count("here, ") # appears 2 times
print gettysburg_address.count("e") # appears 165 times
print gettysburg_address.count("!!!!!!") # doesn't appear at all
########NEW FILE########
__FILENAME__ = string_find
# String methods: string.find()

# string.find() tells you where you can find a part of one string in a larger string.
# string.find() will return a number:
# 		if string.find() returns -1, it could not find the string inside the larger string.
#		otherwise, string.find() will return the slicing number/index of where it found that string

email_address = "hoorayforpython@notarealwebsite.com"

print "I found the snail at: {0}".format(email_address.find("@")) # the slicing number/index of where the at symbol appears

# string.find() + slicing = awesome!

# Everything before the @ is part of the email_handle; everything after the @ is part of the domain where they have their email registered.
# Let's use string.find() and slicing together to split those apart.

at_symbol_index = email_address.find("@")

print "I found the snail at: {0}".format(at_symbol_index) # Notice how line 10 and 19 each give the same result, but take a different approach

email_handle = email_address[0:at_symbol_index]

print "The email_handle is: {0}".format(email_handle)

email_domain = email_address[at_symbol_index + 1:] # without the +1, the at symbol would be included. Notice that there is no number after the colon, so Python assumes you want everything to the end.

print "The email_domain is: {0}".format(email_domain)

print "When string.find() can't find a string, it'll give a -1.  So since there's no 'QQQ' in email_address, this will return a -1: {0}".format(email_address.find("QQQ"))
########NEW FILE########
__FILENAME__ = string_format
# String Formatting

# String formatting is how we can use variables (which store information including numbers, strings, and other types of data) inside of strings
# We can do this by using the .format() string method.

# Here's how it works:

# First, we'll need a variable:
name = "Shannon"

# Now, let's insert it into the print statement:
print "My name is {0}".format(name) # This will print "My name is Shannon"

# We'll analyze each part of the syntax in a moment.  For now, why is this preferable to doing a print "My name is Shannon"?

# Using .format() is more flexible and allows your strings to change as your variables change.

# So let's give the name variable a new value.
name = "Pumpkin"

# Now, let's print it again
print "My name is {0}".format(name) # This will print "My name is Pumpkin"

# Remember that Python runs commands from top to bottom, left to right.

# The two new parts of this print statement are the {0} and the .format(name)

# The {0} is a placeholder for the 0th variable in the list that appears inside the parentheses of .format() -- remember Python starts counting at 0, not 1
# So it really just keeps the spot warm.

# To see why it's {0}, let's define a few more variables.

age = 100
location = "The Pumpkin Patch"

# Now if we want to include those variables, we'll need to put placeholders in the string as well.
print "My name is {0} and my age is {1} and I live in {2}".format(name, age, location)

# Note how we put the placeholders exactly in the string where we want them; and the variables go inside the parentheses of the .format()

# Remember how Python counts.
# So {0} is a placeholder for name;
# {1} is a placeholder for age;
# and {2} is a placeholder for location

# If we had more variables to include, we'd continue in the same way.

# But there's more than one way to do this:
print "My name is {name} and my age is {age} and I live in {location}".format(name=name, age=age, location=location) # This way feels more explicit

# Only some of the ways string formatting is used are covered here. If you'd like to continue to learn all of the ways to use it:
# This is a great guide for lots of different string formatting options: http://ebeab.com/2012/10/10/python-string-format/
#	NOTE: Their examples using the print statement use Python version 3; since we're using 2.7, any time you see print("something") in their examples, using print "something" instead

########NEW FILE########
__FILENAME__ = string_lower
# String methods: string.lower()

# string.lower() is used for turning all characters in your string lowercase.
# There are some related string methods too, like string.upper()

name = "SHANNON!!"

print name.lower() # shannon!!
print name # it's back to the original of SHANNON!!

# To make the changes stick:
name = name.lower()

print name # shannon!!


# string.upper() will turn all characters in your string uppercase but otherwise works in the same manner as string.lower()

greeting = "hello, hi" # not very exuberant ...

print greeting.upper() # MUCH BETTER!

# Making the changes stick:
greeting = greeting.upper()

print greeting # HELLO, hi


# string.lower() and .upper() are primarily used for testing strings in a case-insensitive manner

gender = 'F'

if gender.lower() == 'f':
    print "Hi lady!"

# To accomplish the same thing without string.lower(), you would have to do:
if gender == 'F' or gender == 'f':
    print "Hi lady!"
########NEW FILE########
__FILENAME__ = string_replace
# String methods: string.replace()

# string.replace() is similar to the find -> replace feature in Word, Excel, or other office-y type programs

song = "eat, eat, eat, apples and bananas"

# Let's start here:
print "I like to ... {0}".format(song)


# string.replace() lets us replace all instances of one string with another.
print "I like to ... {0}".format(song.replace("a","o")) # We're replacing all of the lowercase *a*s in song with *o*s

# Let's take a look at the syntax.
# We've seen the {0} syntax; that's the placeholder that string.format() uses to insert a variable into the string that comes before the dot in .format()
# The 0 corresponds to the first variable in the list inside the parentheses (remember that Python starts counting at zero)
# What's the variable we're going to insert at {0}? It's song.replace("a", "o")
# Python will evaluate song.replace("a", "o") and place the result inside of the {0}
# How song.replace("a", "o") works is: .replace() will replace every "a" it finds in song with an "o"
# The way I remember it is .replace() will perform its action on what comes before the dot (which in song.replace("a", "o"), is song)

print "But note that the original song itself is unchanged: {0}".format(song)

print "string.replace() is case-sensitive."
print song.replace("Eat", "chop") # This won't replace anything!

print song
print song.replace("eat", "chop")
print song # the original is unchanged

# If you want your changes to stick, you'll need to assign your variable song a new value
song = song.replace("eat", "chop")
# What we're saying here is essentially:
# song is now equal to the new value of song.replace("eat", "chop")

# If you have lots of replaces to do on a string, you *could* do it like this:
song = song.replace("apples", "mangos")
song = song.replace(" and", ", pears, and")
song = song.replace("bananas", "kiwis")

print song

# Or, you could chain lots of replaces together -- remember that what gets replaced is what comes before the dot!
# In other words, replaces will occur in left-to-right order
song = "eat, eat, eat, apples and bananas" # setting it back to the original
song = song.replace("eat", "chop").replace("apples", "mangos").replace(" and", ", pears, and").replace("bananas", "kiwis")

print song
########NEW FILE########
__FILENAME__ = happy_hour
# Happy Hour!
# Change the age to change the behavior of this program

age = 30

if age >= 21:
    print "I would like a three philosophers, please"
elif age >= 18: # If age is less than 21 but greater than or equal to 18
    print "I'm here to vote -- you can vote at bars, right?"
else:
    print "I really shouldn't even be here but can I have a cherry coke please?"
########NEW FILE########
__FILENAME__ = life
# What you can do in life
# Change the age and gender to change the behavior of this program

# Note the indentation levels and the nesting of different if and elif statements.

age = 10
gender = 'f'

if age < 2:
    print "You can eat and poo all day and people will fall all over themselves over how adorable you are"

elif age == 2:
    print "You can throw tantrums and it's pretty much expected"

elif age == 3:
    print "By this point, you are the master of object permanence."

elif 4 <= age <= 6: # is age between 4 and 6?
    print "This seems like a good time to learn how to read."

    if age == 4:
        print "How about some preschool?"
    elif age == 5:
        print "Kindergarten is cool -- nap time rocks.  Don't forget to share."
    elif age == 6:
        print "First grade.  Naptime is a thing of the past. You're probably too stubborn to be upset much by this."

elif 7 <= age <= 9: # is age between 7 and 9?
    print "Grade school goes by so quickly"

elif 10 <= age <= 11: # is age between 10 and 11?
    print "Middle school is kind of neat."

    if age == 10:
        print "Health class for the first time ..."

        if gender.lower() == 'f':
            print "... Well, that explains a lot, really."
        elif gender.lower() == 'm':
            print "Wonder what the girls are all talking about?"

    elif age == 11:
        print "The periodic table is SO COOL"

elif 12 <= age <= 13: # is age between 12 and 13?
    print "Junior high, aka welcome to hormone land"
    print "PS: sucks to be you"

elif 14 <= age <= 17: # is age between 14 and 17?
    print "High school was probably the worst"
    print "Why on earth did everyone say it was the best time of their life?"

    if age >= 16:
        print "But you can drive, so you've got that going for you"

elif age == 18:
    print "So you're technically an adult now. But not really."
    print "But you can vote, so you've got that going for you."
    print "PS: you have responsibilities now. sucks to be you"

    if gender.lower() == 'm':
        print "Better register for the draft."

elif 19 <= age <= 20:
    print "Now's a good time to be in college."

elif age == 21:
    print "Well, you can drink now."

elif 22 <= age <= 24:
    print "Graduating college and spoiling your liver, mostly."

elif age == 25:
    print "You can rent a car now.  You know, that's never actually come up for me, but apparently it's a thing ..."

else: # In all other cases not covered by the ifs and elifs above

    print "You're an adult.  Do what you want."

    if age > 30 and gender.lower() == 'f': # Note that both of these conditions must be true
        print "Meddling folks are going to start hectoring you about your love life.  Yawn."

    # Notice how the if statements below are all evaluated independently

    if age > 40:
        print "You're over the hill"

    if age > 50:
        print "Everything hurts and your children never call."

    if age > 70:
        print "You're old enough not to care about anything.  You can now do what you like with total impunity."
########NEW FILE########
__FILENAME__ = volunteer_recruitment
# Volunteer recruitment
# Change these variables to change the behavior of your program
volunteers_goal = 20
current_volunteers = 100

# Is current_volunteers less than, equal to, or greater than volunteers_goal?

if current_volunteers < volunteers_goal:
    print "You still have {0} volunteers to recruit!".format(volunteers_goal - current_volunteers)
elif current_volunteers == volunteers_goal:
    print "You met your goal exactly! Way to go!"
elif current_volunteers > volunteers_goal:
    print "You exceeded your recruitment goals by {0}! Way to go!".format(current_volunteers - volunteers_goal)
########NEW FILE########
__FILENAME__ = list_basics
# list basics: adding items, removing items, inserting items, slicing

names = [] # an empty list
print names

names.append('Shannon') # add one item to the end of the list
print names

# Accessing names by slicing:
print names[0] # Shannon

# Inserting an item (not just adding it to the end):
names.insert(0, 'Finn')
print names

# 0 is the slicing number for where you'd like to insert the item BEFORE
# In other words, this will insert 'Finn' just *before* index 0

many_more = ['Jake', 'Princess Bubblegum', 'Marceline the Vampire Queen', 'Peppermint Butler']

# Now we can add all of the names in many_more the end of the list
names.extend(many_more)
print names

# Now we're going to go sugar-free, so everyone from the candy kingdom needs to go.
# Let's remove Peppermint Butler and Princess Bubblegum from our list.

names.pop() # this will remove the last item from the list, which happens to be Peppermint Butler
print names

names.pop(3) # this will remove the item at slicing number / index 3, which is Princess Bubblegum
print names

# Now we're going to search for an item and remove it.
remove_this = names.index('Jake')
print "I found Jake at slicing number / index #{0}".format(remove_this)
print "Now I can use .pop() to remove that item."
names.pop(remove_this)
print names

# We can also use .remove() to shortcut that.
names.remove('Finn')
print names
########NEW FILE########
__FILENAME__ = list_deduplicate
# De-duplicating a list

# De-duplicating list is one of the most commonly used actions in computer programming

# Here, we have a list of state abbreviations ... but our list has lots of duplicates!
list_with_duplicates = ['CT', 'DE', 'MN', 'OH', 'CT', 'OK', 'MT', 'FL', 'TX', 'CT', 'OK', 'TX', 'PA', 'OK']

# First we convert our list with duplicates to the set type, which will eliminate the duplicates
# Next we convert that set back to a list so we can use it as intended.
list_without_duplicates = list(set(list_with_duplicates))

print "List with duplicates: {0}".format(list_with_duplicates)

print "List without duplicates: {0}".format(list_without_duplicates)
########NEW FILE########
__FILENAME__ = 12days

# Twelve Days of Christmas, Python style

gifts = ["A partridge in a pear tree",
         "Two turtle doves",
         "Three french hens",
         "Four colly birds",
         "Five golden rings",
         "Six geese-a-laying",
         "Seven swans-a-swimming",
         "Eight maids-a-milking",
         "Nine ladies dancing",
         "Ten lords-a-leaping",
         "Eleven pipers piping",
         "Twelve drummers drumming"
         ]

gifts_given = []

for day in range(1,13): # identical to the statement   for day in [1,2,3,4,5,6,7,8,9,10,11,12]:

    gifts_given.extend(gifts[:day]) # use list.extend() when adding one or more items to the end of a list; use append to add a single item to a list.
    # If you were to use .append() instead of .extend() here, you would get a list of lists -- not exactly what we want in this case.

    if day == 1:
        suffix = "st"
    elif day == 2:
        suffix = "nd"
    elif day == 3:
        suffix = "rd"
    elif day >= 4:
        suffix = "th"

    print "---------------------------------------------------------"
    print "On the {0}{1} day of Christmas, my true love gave to me: ".format(day, suffix)
    print "---------------------------------------------------------"

    print "\t" + "\n\t".join(reversed(gifts[:day]))

print "---------------------------------------------------------"
print "The gifts I have received in total are: "
print "---------------------------------------------------------"

print "\t" + "\n\t".join(sorted(gifts_given))

print "---------------------------------------------------------"
print "Over all twelve days I received: "
print "---------------------------------------------------------"

total_gifts = 0

for repetitions, day in zip(reversed(range(1,13)), range(1,13)):
    print "{0} of {1}".format(repetitions * day, gifts[day-1][gifts[day-1].index(' ')+1:]) # Complex slicing going on here!
    total_gifts += repetitions * day

print "I received {0} gifts in total".format(total_gifts)

# Complex Slicing Note:

# The first word in each gift is how many was received on that day.
# So I can access the gift itself (and not the number received) by
# slicing past the index of the first space in each string.

# gifts[day-1] is the current gift, which is a string containing the name of the gift (including the number)
# Slicing on that string (beginning at the index of where the first space occurs) lets us take out the number and just get the gift itself.

# So in other words:

# gifts = ["A partridge in a pear tree", ... ]
# Since gifts is a list, we can access the gift items by slicing.

# gifts[2] is a string, "Three french hens"
# gifts[2][0] is a string, "T"

# But we don't want to start at gifts[2][0].
# We want to start at gifts[2][5] - but it won't be 5 each time; it will be different for each gift.

# If we did a "Three french hens".index(' ')+1, we would get the index just past the first space that appears.

# So we insert that into the second slice index, and add the : to ensure that it continues through until the end.

# So: gifts[day-1][gifts[day-1].index(' ')+1:]

########NEW FILE########
__FILENAME__ = calendar
months_in_year = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# Note how in line 6 we slice on the list we are looping over instead of looping over the entire list of months.
for month in months_in_year[0:6]: # For each month in the first six months ...
		print "\n"
		print month
		print "\n"

		for week in range(1, 5):
				print "Week {0}".format(week)

				# Notice that we're slicing again in line 15 instead of looping over the entire week.
				for day in days_of_week[-2:]: # For the last two days of the week (Saturday and Sunday)
						print day

# By removing the slicing from lines 6 and 15, we get the full year (or at least 12 months with 4 weeks of 7 days)
########NEW FILE########
__FILENAME__ = enumerate
# enumerate() example

# enumerate() is used to loop through a list, and for each item in that list, to also give the index where that item can be found

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# This is how we're used to looping -- for each item in this list, print this item
for day in days:
	print day


# Now we add a layer of complexity.  Notice how two variables (index, day) are being created by the for loop.
for index, day in enumerate(days):
	print "days[{0}] contains {1}".format(index, day)
	print "day contains {0}".format(day)


# Since we humans aren't counting days by zero, we do a little addition inside the .format()
for index, day in enumerate(days):
	print "{0} is day # {1}".format(day, index+1)
########NEW FILE########
__FILENAME__ = for_quadrants
# start by creating four lists of your quadrants.  we'll learn a better way to do this next lesson.

nw_addresses = []
ne_addresses = []
sw_addresses = []
se_addresses = []
no_quadrant = []

for entry in range(3): # do this three times:
    address = raw_input("What is your address? ") # get the address from the user

    address = address.split(" ") # split address into a list based on the spaces

    if 'NW' in address:
        nw_addresses.append(' '.join(address)) # if 'NW' appears in address, add the address (joined back as a string) to the proper list

    elif 'NE' in address:
        ne_addresses.append(' '.join(address))

    elif 'SW' in address:
        sw_addresses.append(' '.join(address))

    elif 'SE' in address:
        se_addresses.append(' '.join(address))

    else:
        # In all other instances

        no_quadrant.append(' '.join(address))


print "NW addresses include: {0}".format(nw_addresses)
print "NE addresses include: {0}".format(ne_addresses)
print "SW addresses include: {0}".format(sw_addresses)
print "SE addresses include: {0}".format(se_addresses)
print "Addresses without a quadrant include: {0}".format(no_quadrant)

# Things to think about:

# 1) Which list would 1500 CORNWALL ST be added to? Why is that?

# 2) In other words, how does the 'in' operator work when you use it on a string versus on a list?

# 3) Thinking about it another way, if you commented out line 12 and ran that address through, you'd get a different result.
########NEW FILE########
__FILENAME__ = loops

def loop_example(list_to_loop_through):

    """ Assuming each item in list_to_loop_through is a number, return a list of each item in that list squared. """

    print "I'm going to begin to loop through this list: ", list_to_loop_through, "\n"

    list_items_squared = []

    for each_item in list_to_loop_through:

        print "Now I'm on: ", each_item
        print "{0} squared is {1}\n".format(each_item, each_item**2)
        
        list_items_squared.append(each_item**2)

    print "Now I'm done looping through the list, and I'm going to return the new list, where each list item has been squared."

    return list_items_squared


##Sample Output
##
##>>> my_list = [1, 3, 4, 5, 6, 78, 2334]
##>>> loop_example(my_list)
##I'm going to begin to loop through this list:  [1, 3, 4, 5, 6, 78, 2334]
##Now I'm on:  1
##1 squared is 1
##
##Now I'm on:  3
##3 squared is 9
##
##Now I'm on:  4
##4 squared is 16
##
##Now I'm on:  5
##5 squared is 25
##
##Now I'm on:  6
##6 squared is 36
##
##Now I'm on:  78
##78 squared is 6084
##
##Now I'm on:  2334
##2334 squared is 5447556
##
##[1, 9, 16, 25, 36, 6084, 5447556]

########NEW FILE########
__FILENAME__ = loops_gif
days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
foods_of_day = ['Manicotti', 'Tacos', 'Waffles', 'Raspberries', 'Franks', 'Salad', 'Soup']

# Example #1
for day in days_of_week:
    print "Today is {0}".format(day)
print "\n"


# Example #2: Enumerate (gives the index of the list item)
for (index, day) in enumerate(days_of_week):

    print "Today is the {0}th day of the week, which is {1}".format(index, day) # Please pardon/ignore 0th day and the grammar for "1th", "2th", "3th"

    # In this loop using enumerate, we can access the values of list items in two ways: directly using the looping variable day (which is preferred), or using the index.

    print "So day_of_week[{0}] is: {1}, which is the same as day, which is: {2}".format(index, days_of_week[index], day)
print "\n"

# Example #3: Zip
for (day, food) in zip(days_of_week, foods_of_day):
    print "Today is {0} so obviously I'm having {1} for dinner.".format(day, food)

# NOTE: zip relies on each list being the same length! If the lists are not the same length, zip will only loop through as many items as are in the shorter list!

########NEW FILE########
__FILENAME__ = while_menu


instructions = """Type a one-letter command and hit enter:
A to add a name to your list
R to remove a name from your list
S to show the names in your list
Q to quit 
>"""

allowed_commands = ['a', 'r', 's', 'q']
names = []

command = raw_input(instructions)

while command.lower() in allowed_commands:
    
    if command.lower() == 'a':
        name = raw_input("Enter a name to add to your list: ")
        names.append(name)
    elif command.lower() == 'r':
        name = raw_input("Enter a name to remove from your list: ")
        names.pop(names.index(name)) # this will remove the first instance of this name that appears; if there are duplicates, only the first one will be removed
    elif command.lower() == 's':
        print '\n'.join(names)
    elif command.lower() == 'q':
        break # this will break out of the while loop

    command = raw_input(instructions)
########NEW FILE########
__FILENAME__ = while_quadrants

nw_addresses = []
ne_addresses = []
sw_addresses = []
se_addresses = []
no_quadrant = []

address = raw_input("Enter an address: ")

while address.strip() != "": # every time it reaches the end of the loop it will ask: once you've stripped away all of the extra whitespace, is address an empty string?
    
    address = address.split(" ") # split address into a list based on the spaces

    if 'NW' in address:
        nw_addresses.append(' '.join(address)) # if 'NW' appears in address, add the address (joined back as a string) to the proper list

    elif 'NE' in address:
        ne_addresses.append(' '.join(address))

    elif 'SW' in address:
        sw_addresses.append(' '.join(address))

    elif 'SE' in address:
        se_addresses.append(' '.join(address))

    else:
        # In all other instances

        no_quadrant.append(' '.join(address))

    address = raw_input("Enter an address: ") # It's very important that we include this line to give it a chance to change the value the while loop checks.


print "NW addresses include: {0}".format(nw_addresses)
print "NE addresses include: {0}".format(ne_addresses)
print "SW addresses include: {0}".format(sw_addresses)
print "SE addresses include: {0}".format(se_addresses)
print "Addresses without a quadrant include: {0}".format(no_quadrant)

# This is pretty similar to the for_quadrants.py example, but there are some key differences.

# Most notably, in for_quadrants.py, you need to specify how many addresses to accept.
# This program will allow you to continue to enter addresses until you enter a blank line
# On older computers, this is somewhat similar to how they made the "Press any key to continue" work
########NEW FILE########
__FILENAME__ = zip_bingo
# Basic bingo using zip()

words = ['apple', 'banana', 'carrot', 'danke', 'elephant', 'fruit', 'gorilla', 'horse, michael', 'ice cream', 'jack, one eye', 'kazoo', 'lollerskates', 'mango', 'noodles', 'oboe', 'porcupine', 'quill', 'rowboat', 'sailboat', 'trolley', 'umbrella', 'voltage', 'watermelon', 'xylophobe', 'yarn', 'zebra-clops']

print "words has {0} words in the list.".format(len(words))

output = ''

# Normal for loops allow you to loop over a list and do something for each item in that list.
# A for loop using zip() allows you to loop over multiple lists and do something with each item in those lists at the same time.
# Normally, you'll want to do that with lists that are the same size.  But it still works if one list is shorter; it just behaves a little differently.

# In this case, words is 26 items long and range(25) is 25 items long
# So the for loop will only run 25 times in this case.

# No matter how many more items you add to words, your bingo board should only have 25 squares.

# If you uncomment lines #19 and #20, you'll get a random bingo board every time you run!
# import random
# random.shuffle(words)

for word, position in zip(words, range(25)):

	if position == 12:
		output += 'Free space,'
	else:
		output += "{0},".format(word)

	if position in (4,9,14,19,24):
		output += "\n"

print output

# apple,banana,carrot,danke,elephant,
# fruit,gorilla,horse, michael,ice cream,jack, one eye,
# kazoo,lollerskates,Free space,noodles,oboe,
# porcupine,quill,rowboat,sailboat,trolley,
# umbrella,voltage,watermelon,xylophobe,yarn,
########NEW FILE########
__FILENAME__ = join
states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "District Of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "PALAU", "Pennsylvania", "PUERTO RICO", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

# .join() is a string method (a function that works only on strings) that glues together a list back into a string.

# .join() has two main parts to it: the glue and the list

# The glue is the string that you'd like to glue in between each piece of the list as you're putting it back together as a string.
# The glue is the string that goes just before the dot.

# The list is the list you'd like to glue back together.

# So if we ran the following command:
print "glue".join(states)

# We'd get:
#AlabamaglueAlaskaglueArizonaglueArkansasglueCaliforniaglueColoradoglueConnecticutglueDelawareglueDistrict Of ColumbiaglueFloridaglueGeorgiaglueHawaiiglueIdahoglueIllinoisglueIndianaglueIowaglueKansasglueKentuckyglueLouisianaglueMaineglueMarylandglueMassachusettsglueMichiganglueMinnesotaglueMississippiglueMissouriglueMontanaglueNebraskaglueNevadaglueNew HampshireglueNew JerseyglueNew MexicoglueNew YorkglueNorth CarolinaglueNorth DakotaglueOhioglueOklahomaglueOregongluePALAUgluePennsylvaniagluePUERTO RICOglueRhode IslandglueSouth CarolinaglueSouth DakotaglueTennesseeglueTexasglueUtahglueVermontglueVirginiaglueWashingtonglueWest VirginiaglueWisconsinglueWyoming

# Funny (and helpful for remembering), but that doesn't look very good.

# Instead, let's use a useful piece of glue.  Let's glue it back together with a newline between each state.
print "\n".join(states)

# Now we get:
# Alabama
# Alaska
# Arizona
# Arkansas
# California
# Colorado
# Connecticut
# Delaware
# District Of Columbia
# Florida
# Georgia
# Hawaii
# Idaho
# Illinois
# Indiana
# Iowa
# Kansas
# Kentucky
# Louisiana
# Maine
# Maryland
# Massachusetts
# Michigan
# Minnesota
# Mississippi
# Missouri
# Montana
# Nebraska
# Nevada
# New Hampshire
# New Jersey
# New Mexico
# New York
# North Carolina
# North Dakota
# Ohio
# Oklahoma
# Oregon
# PALAU
# Pennsylvania
# PUERTO RICO
# Rhode Island
# South Carolina
# South Dakota
# Tennessee
# Texas
# Utah
# Vermont
# Virginia
# Washington
# West Virginia
# Wisconsin
# Wyoming
########NEW FILE########
__FILENAME__ = split
address = "1600 Pennsylvania Ave NW Washington, DC"

# .split() is a string method (a function that works only on strings) that splits a string into a list based on some delimiter.
# In this example, we're splitting address into a list at every space.
address = address.split(" ")

# Address is now a list equal to:
# ['1600', 'Pennsylvania', 'Ave', 'NW', 'Washington,', 'DC']
# Note that the list created is a list of strings.

# And since it's a list, you can loop over it!

# .split() is commonly used to split text files into a list (at each newline)
# .split() is also commonly used to split spreadsheet files in comma separated value (CSV) format into a list (at each comma)

# Any time you need to split a string into multiple parts, you can use .split()
########NEW FILE########
__FILENAME__ = read_csv
# If you're new to file handling, be sure to check out with_open.py first!
# You'll also want to check out read_text.py before this example.  This one is a bit more advanced.

with open('read_csv.csv', 'r') as states_file:
    
    # Instead of leaving the file contents as a string, we're splitting the file into a list at every new line, and we save that list into the variable states
    states = states_file.read().split("\n")
    
    # Since this is a spreadsheet in comma separated values (CSV) format, we can think of states as a list of rows.
    # But we'll need to split the columns into a list as well!

    for index, state in enumerate(states):
        states[index] = state.split(",")

# Now we have a nested list with all of the information!

# Our file looks like this:
# State, Population Estimate, Percent of Total population
# California, 38332521, 11.91%
# Texas, 26448193, 8.04%
# ...

# Our header row is at state[0], so we can use that to display the information in a prettier way.
for state in states[1:]: # We use [1:] so we skip the header row.

    # state[0] is the first column in the row, which contains the name of the state.
    print "\n---{0}---".format(state[0])

    for index, info in enumerate(state[1:]): # We use [1:] so we don't repeat the state name.
        print "{0}:\t{1}".format(states[0][index+1], info)

    # states is the full list of all of the states.  It's a nested list.  The outer list contains the rows, each inner list contains the columns in that row.
    # states[0] refers to the header row of the list
    # So states[0][0] would refer to "State", states[0][1] would refer to "Population Estimate", and states[0][2] would refer to "Percent of total population"

    # state is one state within states. state is also a list, containing the name, population, and percentage of that particular state.
    # So the first time through the loop, state[0] would refer to "California", state[1] would refer to 38332521, and state[2] would refer to 11.91%
    # Since state is being create by the for loop in line 24, it gets a new value each time through.

    # We're using enumerate to get the index (slicing number) of the column we're on, along with the information.
    # That way we can pair the column name with the information, as shown in line 30.
    # NOTE: Since we're slicing from [1:] in line 29, we need to increase the index by + 1, otherwise our headers will be off by one.

# Sample output:

# ---"California"---
# "Population Estimate":  38332521
# "Percent of Total population":  "11.91%"

# ---"Texas"---
# "Population Estimate":  26448193
# "Percent of Total population":  "8.04%"

# ---"New York"---
# "Population Estimate":  19651127
# "Percent of Total population":  "6.19%"
########NEW FILE########
__FILENAME__ = read_text
# If you're new to file handling, be sure to check out with_open.py first!

with open('states.txt', 'r') as states_file:
    states = states_file.read().split("\n")

print states

# .read() is a file method that reads the file (which file? the one in the file object just before the dot) and returns the whole contents as a string.

# Instead of leaving it as a string, we're splitting the file into a list at every new line, and we save that list into the variable states

# Now we can loop over that list!

for state in states:
    print state
########NEW FILE########
__FILENAME__ = states_enumerate
with open("states.csv", "r") as states_file:        
    states = states_file.read().split("\n")

for index, state in enumerate(states):
    states[index] = states[index].split(",")

    print "{0}'s abbreviation is {1}".format(states[index][1], states[index][0])    

# print states

########NEW FILE########
__FILENAME__ = with_open
with open('states.txt', 'r') as states_file:
    states = states_file.read()

print states

# *with* is a special Python keyword that's used to create a "container" that will automatically close your file when the indentation level is broken.
#   So in line 1, the file 'states.txt' is opened, and the variable states_file is created.
#   states_file is a *file object*, which shouldn't be too scary.  We've worked with string objects and list objects without even realizing it!
#   String objects and list objects are different ways of storing information in Python, and each has its own set of functions that only work with that type of thing.
#   So string objects have string methods like .find() and .replace() -- functions that only work on strings.
#   List objects have list methods like .append() and .pop() -- functions that only work on lists.
#   We use with open('states.txt') as states_file to create a *file object*, and file objects have file methods -- functions that only work on files.

# open() is a special built-in Python function that tells Python to open a file.
#   open() can take up to two arguments/parameters.
#   The first parameter is the file you want to open.
#       If the file you want to open and the script that you're running are in the same folder, you can just say the filename, as we did in line 1.
#       Otherwise, you'll need to give Python more details on where it can find the file -- either using the full pathname of the file,
#       Or just the path from where it's looking right now. (section_07_(files))

#   The second parameter tells Python how to open the file.  This parameter is a string.
#       There are three common ways to open the file, and we'll discuss those first.
#           r: read-only mode.  Python won't make any changes to this file, but you can read from it.
#           w: write mode. If the file doesn't exist, Python will create a new file with that name.  Otherwise, Python will overwrite the existing file.
#           a: append mode. If the file doesn't exist, Python will create a new file with that name. Otherwise, Python will append to the end of the existing file.
#       And still important, but less common:
#           b: binary mode.  Use this when reading from a non-text file, like an image.

# .read() is a file method that reads the file (which file? the one in the file object just before the dot) and returns the whole contents as a string.
# In line 2 we save the entire file contents as a string, states
########NEW FILE########
__FILENAME__ = write_population
# If you're new to file handling, be sure to check out with_open.py first!
# You'll also want to check out read_text.py before this example.  
# You'll also want to check out read_csv.py before this example.  This one is a bit more advanced, and builds off read_csv.py.

with open('read_csv.csv', 'r') as states_file:
    
    # Instead of leaving the file contents as a string, we're splitting the file into a list at every new line, and we save that list into the variable states
    states = states_file.read().split("\n")
    
    # Since this is a spreadsheet in comma separated values (CSV) format, we can think of states as a list of rows.
    # But we'll need to split the columns into a list as well!

    for index, state in enumerate(states):
        states[index] = state.split(",")

# Now we have a nested list with all of the information!

# Instead of printing out the information as in read_csv.py, let's save it to a new file instead.

with open('states_pop.txt', 'w') as population_file:

    # In line 20, we create the file in a similar way to opening the file -- the only difference being the write flag (second parameter)
    # Line 20 creates a new variable called population_file, which is a file object.

    # .read() is a file method that we're pretty familiar with by now, but there's also .write()

    # .write() is a file method that allows us to write a string to a file.

    # Our header row is at state[0], so we can use that to display the information in a prettier way.
    for state in states[1:]: # We use [1:] so we skip the header row.

        # state[0] is the first column in the row, which contains the name of the state.
        population_file.write("\n---{0}---\n".format(state[0])) # Instead of printing the string, we're now writing the string to the file.

        for index, info in enumerate(state[1:]): # We use [1:] so we don't repeat the state name.
            population_file.write("{0}:\t{1}\n".format(states[0][index+1], info)) # Instead of printing the string, we're now writing the string to the file.

# Note that we had to add in some extra newlines compared to in read_csv.py; when printing, Python is generous with newlines.
# But when you're writing to a file, Python doesn't assume you want those newlines in, and you'll have to add them in yourself.
########NEW FILE########
__FILENAME__ = csv_to_dict

def csvtodict(filename):
    
    with open(filename, 'r') as csv_file:
        text = csv_file.read().strip().split('\n')

    header_row = text[0].split(',')

    dictionary = {}

    for row, line in enumerate(text[1:]):

        dictionary[row] = {}

        for col, cell in enumerate(line.split(',')):

            dictionary[row][header_row[col]] = cell


    return dictionary


print csvtodict('events.csv')

########NEW FILE########
__FILENAME__ = division
def division(x, y):
    if y == 0:
        return # You can't divide by Zero! If you do, you'll get an error.
    return x/y # It's implied that this only happens when y != 0, since otherwise the function would have ended at line 3
########NEW FILE########
__FILENAME__ = dropdown_states

def dropdown_states():
    
    """ What's a string doing all by itself, you ask? 
        Shouldn't I be attached to a variable?

        Well I'm a special string that Python looks for at the very beginning of a function.
        I'm used to describe the function.

        This function will return a string with an HTML drop-down menu of US states.
    """

    states = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']
    abbreviations = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

    output = ['<select>']

    for state, abbreviation in zip(states, abbreviations):
        output.append('\t<option value="{0}">{1}</option>'.format(abbreviation, state))

    output.append('</select>')

    output = '\n'.join(output) # Glue together the list with a newline between each list item.

    return output
########NEW FILE########
__FILENAME__ = open_csvfile
def open_csvfile(filename, delimiter=','):

    with open(filename, "r") as csv_file:        
        rows = csv_file.read().split("\n")

    for index, row in enumerate(rows):
        rows[index] = row.split(delimiter)

    return rows
########NEW FILE########
__FILENAME__ = remove_duplicates
def remove_duplicates(from_list):

    """ 
        The function list() will convert an item to a list. 
        The function set() will convert an item to a set.

        A set is similar to a list, but all values must be unique.

        Converting a list to a set removes all duplicate values.
        We then convert it back to a list since we're most comfortable working with lists.

    """

    from_list = list(set(from_list))

    return from_list

    

########NEW FILE########
__FILENAME__ = textfile_to_string
def textfile_to_string(filename):

    with open(filename, "r") as text_file:      
        text = text_file.read()

    return text
########NEW FILE########
__FILENAME__ = dict_access
# This is probably the best place to start with dictionaries.

# First, let's create a string, a list, and a dictionary.

name = "Shannon"

attendees = ['Shannon', 'Amy', 'Jen', 'Julie']

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

# We can access part of a string using slicing:
print name[0] # S

# We can access part of a list using slicing:
print attendees[0:2] # Shannon, Amy

# We can access part of a dictionary if we know its key.
print contacts['Jen'] # 301-600-5555

# In lines 9-14, we created a dictionary.
# Dictionaries are another way of storing information in Python.
# Dictionaries are made up of key+value pairs.

# In the dictionary contacts, the keys are Shannon, Amy, Jen, and Julie.
# A dictionary's keys are strings that you can use to see the contents.
# A dictionary's values can be any type of information - a string, a list, a number, even a dictionary!
# That value is tied to the key - it belongs to a key.

# The best way to think about a dictionary is a phone book or a contact list.
# How difficult would it be if we had to store contacts like this?

contacts_as_list = [
    ['Shannon', '202-555-1234'],
    ['Amy', '410-515-3000'],
    ['Jen', '301-600-5555'],
    ['Julie', '202-333-9876']
]

# What if we wanted to get Jen's phone number? It would be a pain to retrieve it!
# We'd have to loop through each item in the list and check the name, like this:

phone_we_want = 'Jen'

for contact in contacts_as_list:
    if contact[0] == phone_we_want:
        print contact[1] # The phone number

# Kind of a pain.  Luckily, dictionaries mean we don't have to do this!

print contacts['Jen']
########NEW FILE########
__FILENAME__ = dict_get
# If you're new to dictionaries, you might want to start with dict_access.py

# We create a dictionary.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

name = raw_input("Enter the name of the person whose phone number you want: ")

print "We will get a KeyError if you entered a name that wasn't in the dictionary."
print "{0}'s number is: {1}".format(name, contacts[name])

print "But there's a way we don't need to worry about KeyErrors."

name = raw_input("Enter the name of the person whose phone number you want ... might I suggest Frankenstein? ")

# .get() is a dictionary method that lets us safely access a dictionary even if that key doesn't exist.

print "{0}'s number is ... {1}".format(name, contacts.get(name, " ... I couldn't find it!"))
########NEW FILE########
__FILENAME__ = dict_items
# If you're new to dictionaries, you might want to start with dict_access.py

# We create a dictionary.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

# We can use the dictionary method .items() to give us a list of all of the items in contacts.

print contacts.items()

# Strictly speaking, .items() doesn't give us a list, it gives us a *tuple*, which is another way of storing information in Python.
# Tuples are almost identical to lists, except they're read-only.  You can't add to/remove from a tuple.
# But they're accessed and used in pretty much the same way, so we're going to treat it as if Python's giving us a list, and it will behave as we expect.

# .items() gives us a key and value pair together - so we can use that directly when we're looping.

for contact, phone in contacts.items():
    print "{0}'s number is {1}".format(contact, phone)

# .items() is probably most commonly used out of .keys(), .values(), and .items() because it gives you both the key and the value together.
########NEW FILE########
__FILENAME__ = dict_keys
# If you're new to dictionaries, you might want to start with dict_access.py

# We create a dictionary.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

# We can use the dictionary method .keys() to give us a list of all of the keys in contacts.

print contacts.keys()

for contact in contacts.keys():
    print "{0}'s number is {1}".format(contact, contacts[contact])

# Dictionaries are unordered, so the keys (and their values) might be in a different order each time.  Or they might not.  Either way, that's normal.

# In other words, you can't rely on the ordering of anything in a dictionary.  But you could apply ordering to the keys.

# The built-in function sorted() will sort a list in ascending order.

for contact in sorted(contacts.keys()):
    print "{0}'s number is {1}".format(contact, contacts[contact])
########NEW FILE########
__FILENAME__ = dict_update
# If you're new to dictionaries, you might want to start with dict_access.py

# We create a dictionary.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

# If we want to add a new item to a dictionary, we can use direct access to change it.
contacts['Rachel'] = '202-888-1234'

# We can do the same thing to change an existing dictionary item, too.
contacts['Amy'] = '703-444-8888'

# That's great for changing a dictionary one key at a time, but let's say we have a lot of updates.  We have two options.

new_contacts = {
    'Kristin': '703-333-1234',
    'Katie': '301-555-9876',
    'Grace': '202-777-2222',
    'Charlotte': '410-555-9999'
}

# Option 1: Loop through the changes one at a time.

for name, phone in new_contacts.items():
    contacts[name] = phone

# Now contacts has everything in new_contacts.
print contacts, "\n"


# Let's set contacts back to the value it had before we added new_contacts.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876',
    'Rachel': '202-888-1234'
}

# Option 2: Use the dictionary method .update()

contacts.update(new_contacts)

print contacts
########NEW FILE########
__FILENAME__ = dict_values
# If you're new to dictionaries, you might want to start with dict_access.py

# We create a dictionary.

contacts = {
    'Shannon': '202-555-1234',
    'Amy': '410-515-3000',
    'Jen': '301-600-5555',
    'Julie': '202-333-9876'
}

# We can use the dictionary method .values() to give us a list of all of the values in contacts.

print contacts.values()

for phone in contacts.values():
    print "{0}".format(phone)

# .values() is used less frequently than .keys() since you can't get the key from the value (but you can get the value if you know the key)

# Use .values() when you don't care what the key is, you just want a list of all of the values.  It's less common, but still good to know.
########NEW FILE########
__FILENAME__ = nested_access
def access(dictionary, nested_keys):

    """ Try to access nested keys within a dictionary.  Returns False instead of a KeyError on failure. 

        Written to avoid needing to do multiple try/except blocks when trying to access specific values in JSON.

        Previously:
            try:
                title = response['response']['docs'][0]['descriptiveNonRepeating']['title']['content']
            except KeyError:
                pass

            # ... and repeating this structure for each variable we'd like to save.  
            # We could wrap the *whole* thing in a try/except, but then it would trigger the except on the first failure.

        Now:
            title = access(response, ['response', 'docs', 0, 'descriptiveNonRepeating', 'title', 'content'])

            # ... and repeating this structure for each variable we'd like to save.

    """

    for index, key in enumerate(nested_keys):

        print index, key

        try:
            if dictionary.has_key(key):
                if nested_keys[index + 1:] != []:
                    return access(dictionary[key], nested_keys[index + 1:])
                else:
                    return dictionary[key]
            else:
                return False
        except AttributeError: # at this point, dictionary is a list, perhaps containing dictionaries
            if key < len(dictionary):
                if nested_keys[index + 1:] != []:
                    return access(dictionary[key], nested_keys[index + 1:])
                else:
                    return dictionary[key]
            else:
                return False
########NEW FILE########
__FILENAME__ = dicts_and_lists
# Dictionaries and lists, together

# Loading from https://raw.githubusercontent.com/shannonturner/education-compliance-reports/master/investigations.json

investigations = {
  "type": "FeatureCollection",
  "features": [

  {
   "type": "Feature",
   "geometry": {
      "type": "Point",
      "coordinates": [
     -112.073032,
     33.453527
        ]
    },
    "properties": {
      "marker-symbol": "marker",
      "marker-color": "#D4500F",
      "address": " AZ ",
      "name": "Arizona State University"
      }
  },

  {
   "type": "Feature",
   "geometry": {
      "type": "Point",
      "coordinates": [
     -121.645734,
     39.648248
        ]
    },
    "properties": {
      "marker-symbol": "marker",
      "marker-color": "#D4500F",
      "address": " CA ",
      "name": "Butte-Glen Community College District"
      }
  },
  ]
}

# The first level is a dictionary with two keys: type and features
# type's value is a string: FeatureCollection
# features' value is a list of dictionaries

# We're going to focus on the features list.

# Each item in the features list is a dictionary that has three keys: type, geometry, and properties

# If we wanted to access all of the properies for the first map point, here's how:
print investigations['features'][0]['properties']
#   list of dictionaries ^       ^        ^
#                first map point |        | properties

# {
#   "marker-symbol": "marker",
#   "marker-color": "#D4500F",
#   "address": " AZ ",
#   "name": "Arizona State University"
# }

# As we see above, properties is itself a dictionary

# To get the name of that map point:
print investigations['features'][0]['properties']['name']

# Arizona State University

# Generally speaking, if what's between the square brackets is a number, you're accessing a list.
# If it's a string, you're accessing a dictionary.
# If you get stuck or are getting errors, try printing out the item and the key or index.
########NEW FILE########
__FILENAME__ = dict_to_json
# Converting Dictionaries (and lists and strings, etc) to JSON

# First, use the built-in library json.  You don't need to pip install this, it comes with python.
import json

# Next, create your dictionary.
# Using some based on https://github.com/shannonturner/python-lessons/tree/master/section_10_(dictionaries)

contacts = [
    {'friends': [
    {'Shannon': {'phone': '202-555-1234', 'twitter': '@svt827', 'github': '@shannonturner'} },
    {'Amy': {'phone': '410-515-3000', 'fax': '410-555-3001', 'email': 'amy@amy.org'} },
    {'Jen': {'phone': '301-600-5555', 'email': 'jen@jen.biz'} },
    {'Julie': {'phone': '202-333-9876'} },
    ],
    'enemies': []}
]

# contacts is a list that holds a dictionary with two keys: friends and enemies
#       friends is a list that holds four dictionaries
#           Shannon is one dictionary, and she has a dictionary for all of the ways to contact her
#           Amy is another dictionary, and she has a dictionary for all of the ways to contact her
#           Jen is another dictionary, and she has a dictionary for all of the ways to contact her
#           Julie is another dictionary, and she has a dictionary for all of the ways to contact her
#       enemies is an empty list

# json.dumps() is used to dump your information stored as dictionaries, lists, and strings into the JSON format
print json.dumps(contacts, indent=4, sort_keys=True)
# indent=4 will indent each level as this many spaces (4), which looks way nicer than not doing this.
# sort_keys=True will sort the keys within the dictionary based on their name

# You might not see the indentation if you print to the terminal; you may need to write the output to a file to see it.
with open('contacts.json', 'w') as json_contacts:
    json_contacts.write(json.dumps(contacts, indent=4, sort_keys=True))
########NEW FILE########
__FILENAME__ = json_to_dict
# Converting Dictionaries (and lists and strings, etc) to JSON

# First, use the built-in library json.  You don't need to pip install this, it comes with python.
import json

# Now, load the file (contacts.json) that you created in https://github.com/shannonturner/python-lessons/blob/master/section_11_(api)/dict_to_json.py
with open('contacts.json', 'r') as contacts_file:
    contacts = contacts_file.read()

print contacts

print "\n\n contacts above is a string"

# Now we have loaded the contents of the file as a string that looks like JSON.
# json.loads() will allow us to load it back into a form Python can use (and loop over)
contacts = json.loads(contacts)

print contacts

print "\n\n now you can loop over contacts, since it is a list (with dictionaries and other goodies nested within)"
########NEW FILE########
__FILENAME__ = using_requests
import requests

title = raw_input("Enter your movie: ")

url = 'http://bechdeltest.com/api/v1/getMoviesByTitle?title={0}'.format(title).replace(" ","+").replace("'","&#39;")

print url

response = requests.get(url).json()

print response

# Search for 'matrix' gives the following JSON response (this is printed at line 11):

# [
#     {
#         u'rating': u'3', 
#         u'submitterid': u'1', 
#         u'imdbid': u'0234215', 
#         u'title': u'Matrix Reloaded, The', 
#         u'dubious': u'0', 
#         u'visible': u'1', 
#         u'year': u'2003', 
#         u'date': u'2008-07-21 00:00:00', 
#         u'id': u'58'
#     },

#     {
#         u'rating': u'3', 
#         u'submitterid': u'1', 
#         u'imdbid': u'0242653', 
#         u'title': u'Matrix Revolutions, The', 
#         u'dubious': u'0', 
#         u'visible': u'1', 
#         u'year': u'2003', 
#         u'date': u'2008-07-21 00:00:00', 
#         u'id': u'59'
#     }, 

#     {
#         u'rating': u'1', 
#         u'submitterid': u'7916', 
#         u'imdbid': u'0303678', 
#         u'title': u'Armitage: Dual Matrix', 
#         u'dubious': u'1', 
#         u'visible': u'1', 
#         u'year': u'2002', 
#         u'date': u'2013-08-01 15:26:03', 
#         u'id': u'4429'
#     }, 

#     {
#         u'rating': u'3', 
#         u'submitterid': u'1', 
#         u'imdbid': u'0133093', 
#         u'title': u'Matrix, The', 
#         u'dubious': u'0', 
#         u'visible': u'1', 
#         u'year': u'1999', 
#         u'date': u'2008-07-20 00:00:00', 
#         u'id': u'36'
#     }
# ]

# Which is then looped through
for movie in response:
    print movie['title'], movie['rating']

# And printed:
# Matrix Reloaded, The 3
# Matrix Revolutions, The 3
# Armitage: Dual Matrix 1
# Matrix, The 3
########NEW FILE########
__FILENAME__ = exceptions_01
# Example #1: Simple Exception handling

try:
    print 1/0 # This will fail.
except ZeroDivisionError:
    print "You can't divide by zero!"

########NEW FILE########
__FILENAME__ = exceptions_02
# Example #2: Exceptions trigger the except block and skip any code after the error.

try:
    print 1/0 # This will fail.
    print "I'm code that will never run!"

    print 555/0 # This *would* fail, except we never get here.  That's why it's best to use a try block on the fewest lines of code possible.

except ZeroDivisionError:
    print "You still can't divide by zero!"

########NEW FILE########
__FILENAME__ = exceptions_03
# Example #3: Different types of exceptions can be caught.

print "Example #3: Phonebook!"

phonebook = {}

while True: # this will loop forever until we issue a break!

    key = raw_input(" (Ex #3, Phonebook) Please enter a person's name, or leave blank to quit: ")

    if key == '':
        break
    
    value = raw_input(" (Ex #3, Phonebook) Please enter {0}'s phone number with no punctuation: ")

    phonebook[key] = value


user_input = raw_input(" Okay, now we're done entering names. Please enter the name of the person whose number you would like: ")

try:
    print int(phonebook[user_input])
except KeyError:
    print "You don't have {0}'s phone number!".format(user_input)
except ValueError:
    print "You typed in punctuation, didn't you?"
    print "Here's the number anyway ... {0}".format(phonebook[user_input])

########NEW FILE########
__FILENAME__ = exceptions_04
# Example #4: The catch-all handler: Exception

print "Now we'll just repeat the try ... except block from Example #3 but with a catch-all for any exception."

phonebook = {}

while True: # this will loop forever until we issue a break!

    key = raw_input(" (Ex #3, Phonebook) Please enter a person's name, or leave blank to quit: ")

    if key == '':
        break
    
    value = raw_input(" (Ex #3, Phonebook) Please enter {0}'s phone number with no punctuation: ")

    phonebook[key] = value

user_input = raw_input(" Okay, now we're done entering names. Please enter the name of the person whose number you would like: ")

try:
    print int(phonebook[user_input])
except Exception, e:
    print "With any exception type (not just Exception), you can find out the detailed message specific to the error by using ', e' afterward."
    print "In this case, the detailed message was: {0}".format(e)
    print "Exception is best used in addition to other specific exceptions first."
    print "For best results, think of each except as being similar to an 'elif' statement targeting something specific; except Exception is similar to an 'else' statement being the catch-all."

########NEW FILE########
__FILENAME__ = exceptions_05
# Example #5: Nesting exception handling

# Exception handling works the same as any other indentation level in Python

user_input = raw_input(" Example #5: enter a number: ")

try:
    user_input = int(user_input)
except ValueError:
    try:
        print "User input was either a float or a string."
        user_input = int(float(user_input))
        print "Turns out it was a float! {0}".format(user_input)
    except ValueError:
        print "Guess {0} was a string and not a number at all.".format(user_input)

print "Now the code block above works pretty much the same as the following: "

user_input = raw_input(" Example #5: enter a number: ")

try:
    user_input = int(float(user_input))
except ValueError:
    print "Guess {0} was a string and not a number at all.".format(user_input)

########NEW FILE########
__FILENAME__ = exceptions_06
# Example #6: raise (no arguments)

import time

print "I'm going to count down from 1000 as fast as I can.  Hit Ctrl+C three times to stop."

x = 1000
times_paused = 0

while x > 0:

    try:
        print x
        x-=1
    except KeyboardInterrupt:

        times_paused += 1
        
        print " You have paused {0} time(s).".format(times_paused)

        if times_paused == 3:
            print "You paused 3 times.  Ending early by raising the original exception (KeyboardInterrupt)"
            raise # this will raise the *original* exception, which in this case is KeyboardInterrupt

        print "Pausing for {0} seconds.".format(times_paused)
        time.sleep(times_paused)

########NEW FILE########
__FILENAME__ = exceptions_07
# Example #7: try-else

# Use an else block attached to a try block when you want to execute code only when no errors occured.

user_input = raw_input("Please enter a number: ")

try:
    user_input = int(float(user_input))
except ValueError:
    print "You didn't enter a number, did you?"
    
else: # no errors occurred
    print "Hooray! We didn't encounter any errors!"
    print "Oh, by the way, your number was: {0}".format(user_input)

########NEW FILE########
__FILENAME__ = exceptions_08
# Example #8: try-finally

# Use an finally block attached to a try block to execute code no matter what happens

user_input = raw_input("Please enter a number: ")

try:
    user_input = int(float(user_input))

except ValueError:
    print "You didn't enter a number, did you?"
    
else: # no errors occurred
    print "Hooray! We didn't encounter any errors!"

finally: # no matter what
    print "Here was your input: {0}".format(user_input)

print "'finally' isn't that common though, and you could really just put your code outside of the block entirely."
print "Here was your input: {0}".format(user_input) # Like this!

########NEW FILE########
__FILENAME__ = multiple_exceptions
# You can also handle multiple types of exceptions in the same block

# In the example below, changing age at line five will change the behavior of the program.
# If age can be converted to an int, line 13 will run.
# If age is a string, but cannot be converted to an int, a ValueError will occur
# If age is a different type of thing (a dictionary, list, etc), 
#       a TypeError will occur since those cannot be converted into a list

age = '' # try with 100 or with 'x100' or with ['100'] or with None or with False or with {'age': 100}

try:
    age = int(age)
except (TypeError, ValueError) as err:
    print "Invalid entry: {0}; error: {1}".format(age, err)
else:
    print "Your age is: {0}".format(age)
########NEW FILE########
__FILENAME__ = quadrant
def quadrant(address):

    "Returns the DC quadrant for the address given"

    return [quadrant for quadrant in address.split(' ') if quadrant in ['NW', 'NE', 'SW', 'SE']] or None

########NEW FILE########
__FILENAME__ = timestamp

# Getting a timestamp in the format YYYYMMDDHHMMSS

## NOTE: For clarity and consistency, all examples below will use the same timestamp; 2013 October 20 09:38:26

import time

print time.localtime() # time chunks smaller than ten are not zero-padded
    ##time.struct_time(tm_year=2013, tm_mon=10, tm_mday=20, tm_hour=9, tm_min=38, tm_sec=26, tm_wday=6, tm_yday=293, tm_isdst=1)

# The slices that I want are year (slice zero) through second (slice five), so I need the slicing indices [0:6]

print time.localtime()[:6]
    ##(2013, 10, 20, 9, 38, 26

# So my instinct is to use a str.join() to glue together all of the pieces that I want, slices [0:6]

    ##>>> ''.join(time.localtime()[:6])
    ##
    ##Traceback (most recent call last):
    ##  File "<pyshell#9>", line 1, in <module>
    ##    ''.join(time.localtime()[:6])
    ##TypeError: sequence item 0: expected string, int found

# But that instinct turns out to be wrong, because join wants to glue together strings, not ints.


# There are many solutions to this problem.

# Method #1: Looping (the easy but long way)
timestamp = []

for time_chunk in time.localtime()[:6]:
    timestamp.append(str(time_chunk))

print "Method #1: ", ''.join(timestamp)

# Method #2: Passing an arbitrary number of arguments (quick but somewhat ugly)

print "Method #2: ", '{0}{1}{2}{3}{4}{5}'.format(*time.localtime()[:6])

# Method #3: List comprehension

print "Method #3: ", ''.join([str(time_chunk) for time_chunk in time.localtime()[:6]])

########NEW FILE########
