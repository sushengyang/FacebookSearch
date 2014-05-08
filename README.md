FacebookSearch
==============

Augmenting Facebook's graph search with functionality for full-text search of a user's posts.

The best way to access the app is to go to http://facebook-search.herokuapp.com

If you want to deploy locally, add the following entry in your hosts file:
    127.0.0.1  facebook-search.herokuapp.com


Make sure you have Python installed and have the package manager called Pip install. To see if Pip is installed, open up a shell and type 'pip'.
Then we need to install all our dependencies. In the shell, navigate to this project directory (the directory with manage.py in it.) Run the following command. 

    pip install -r requirements.txt

We need the WordNet Corpus for nltk so let's get that now. in the shell run 'python'. Once the python shell opens, run the following.

    nltk.download()

This will open a GUI downloaded for nltk. In the corpus section, get the WordNet Corpus.

Once that is done, we are set to go.
Run the folowing.

    python manage.py syncdb
    python manage.py runserver

Navigate to facebook-search.herokuapp.com:8000 (We mapped this to localhost earlier. This was to tell facebook that this is a legitimate deployment and not an attempt at cross site scripting.)

Login via Facebook and we are good to go.
