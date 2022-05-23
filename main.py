from pydoc import describe
from google.cloud import datastore
import datetime
from flask import Flask, redirect, render_template
import google.oauth2.id_token
from flask import Flask, render_template, request
from google.auth.transport import requests
import uuid
import sys

app = Flask(__name__)

datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


def updateUserInfo(email, name, username, description):
    entity_key = datastore_client.key('UserInfo', email)
    entity = datastore_client.get(entity_key)
    entity.update({
        'name': name,
        'username': username,
        'profile_description': description,
    })
    datastore_client.put(entity)


def createUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'name': "",
        'profile_description': '',
        'username': "",
        'creation_date': datetime.datetime.now(),
        'tweets': [],
        'followers': [],
        'follows': [],
    })
    datastore_client.put(entity)


def create_tweet(email, tweet):

    uniqeId = str(uuid.uuid4())

    # remove dashes and numbers from uniqeId
    uniqeId = uniqeId.replace("-", "")
    uniqeId = uniqeId.replace("0", "")
    uniqeId = uniqeId.replace("1", "")
    uniqeId = uniqeId.replace("2", "")
    uniqeId = uniqeId.replace("3", "")
    uniqeId = uniqeId.replace("4", "")
    uniqeId = uniqeId.replace("5", "")
    uniqeId = uniqeId.replace("6", "")
    uniqeId = uniqeId.replace("7", "")
    uniqeId = uniqeId.replace("8", "")
    uniqeId = uniqeId.replace("9", "")

    entity_key = datastore_client.key('tweet', uniqeId)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'id': uniqeId,
        'email': email,
        'content': tweet,
        'username': retrieveUserInfo(email)['username'],
        'name': retrieveUserInfo(email)['name'],
        'creation_date': datetime.datetime.now(),
    })
    deneme = datastore_client.put(entity)
    return uniqeId


def retrieveUserInfo(email):
    entity_key = datastore_client.key('UserInfo', email)
    entity = datastore_client.get(entity_key)
    return entity


def retrieveUserInfoByUsername(username):
    query = datastore_client.query(kind='UserInfo')
    query.add_filter('username', '=', username)
    return list(query.fetch())


def retrieveTweet(tweetId):
    entity_key = datastore_client.key('tweet', tweetId)
    entity = datastore_client.get(entity_key)
    return entity


def retrieveTweets(email):
    query = datastore_client.query(kind='tweet')
    query.add_filter('email', '=', email)
    query.order = ['-creation_date']
    return list(query.fetch())

# search for tweets by including the word in the tweet content


def searchTweets(word):
    query = datastore_client.query(kind='tweet')
    query.add_filter('content', '=', word)
    query.order = ['-creation_date']
    return list(query.fetch())


def followUser(email, targetEmail):
    user = retrieveUserInfo(email)
    targetUser = retrieveUserInfo(targetEmail)
    if targetEmail == email:
        return
    # look if it is already following
    if targetEmail in user['follows']:
        # remove from follows
        user['follows'].remove(targetEmail)
        targetUser['followers'].remove(email)
    else:
        user['follows'].append(targetEmail)
        targetUser['followers'].append(email)
    datastore_client.put(user)
    datastore_client.put(targetUser)

# return last 50 tweets of following users including the user


def retrieveFollowingTweets(email):
    user = retrieveUserInfo(email)
    tweets = []
    for following in user['follows']:
        followingTweets = retrieveTweets(following)
        for tweet in followingTweets:
            tweets.append(tweet)
    # append current user tweets
    for tweet in retrieveTweets(email):
        tweets.append(tweet)
    # sort tweets by creation date
    tweets.sort(key=lambda x: x['creation_date'], reverse=True)
    return tweets[:50]


def updateTweet(tweetId, content):
    entity_key = datastore_client.key('tweet', tweetId)
    entity = datastore_client.get(entity_key)
    entity.update({
        'content': content,
    })
    datastore_client.put(entity)


def deleteTweet(tweetId):
    entity_key = datastore_client.key('tweet', tweetId)
    datastore_client.delete(entity_key)


@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    tweet = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
            if user_info == None:
                createUserInfo(claims)
                user_info = retrieveUserInfo(claims['email'])
            tweet = retrieveFollowingTweets(user_info['email'])
            if user_info:
                if user_info['username'] == "":
                    return redirect('/update_user')
        except ValueError as exc:
            error_message = str(exc)

    return render_template('index.html', user_data=claims, error_message=error_message,
                           user_info=user_info, tweets=tweet)


@app.route('/update_user', methods=['POST', 'GET'])
def update_user():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None

    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])

        except ValueError as exc:
            error_message = str(exc)

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        description = request.form['profile_description']

        if len(description) > 280:
            error_message = "Description is too long"
        else:
            updateUserInfo(claims['email'], name, username, description)
            return redirect('/')
    else:
        return render_template('update_user.html', user_data=claims, error_message=error_message,
                               user_info=user_info, firstComer=user_info['username'] == "")


@app.route('/tweet', methods=['POST', 'GET'])
def tweet():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None

    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])

        except ValueError as exc:
            error_message = str(exc)

    if request.method == 'POST':
        content = request.form['tweet']
        if len(content) > 280:
            error_message = "Tweet is too long"
            return redirect('/')
        else:
            if user_info != None:
                create_tweet(claims["email"], content)
                return redirect('/')
            else:
                return redirect('/')
    else:
        return render_template('update_user.html', user_data=claims, error_message=error_message,
                               user_info=user_info)


@app.route('/user/<email>')
def user_detail(email):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    follows = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    user = retrieveUserInfo(email)
    user_tweets = retrieveTweets(email)
    # check if the user is following the current user
    if user_info:
        if user_info['username'] == "":
            return redirect('/update_user')
        if email in user_info['follows']:
            follows = True
        else:
            follows = False

    return render_template('user_detail.html', user_data=claims, error_message=error_message,
                           user_info=user_info, user=user, tweets=user_tweets[:50], follows=follows, email=email)


@app.route('/search_user', methods=['POST'])
def search_user():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    search_email = request.form['user']
    if request.form['user'] == "":
        return redirect('/')
    else:
        user = retrieveUserInfo(search_email)
        if user == None:
            user = retrieveUserInfoByUsername(search_email)
            if user != []:
                user = user[0]['email']
        if user:
            return redirect('/user/' + user)
        else:
            error_message = "User not found"
            return redirect('/')


@app.route('/search_tweet', methods=['POST'])
def search_tweet():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    search_word = request.form['tweet']
    tweets = searchTweets(search_word)
    return render_template('search_tweet.html', user_data=claims, error_message=error_message,
                           user_info=user_info, tweets=tweets)


@app.route('/follow', methods=['POST'])
def follow():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    follow_email = request.form['email']
    follow_user = retrieveUserInfo(follow_email)
    if follow_user:
        followUser(claims['email'], follow_email)
        return redirect('/user/' + follow_email)
    else:
        error_message = "User not found"
        return redirect('/')


@app.route('/update_tweet', methods=['POST'])
def update_tweet():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    tweet_id = request.form['tweet_id'].split("'")[3]
    content = request.form['tweet']
    updateTweet(tweet_id, content)
    return redirect('/')


@app.route('/delete_tweet', methods=['POST'])
def delete_tweet():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims['email'])
        except ValueError as exc:
            error_message = str(exc)

    tweet_id = request.form['tweet_id'].split("'")[3]
    deleteTweet(tweet_id)
    return redirect('/')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
