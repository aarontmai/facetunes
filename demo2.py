import random
import json
import spotipy
import webbrowser
import subprocess
import sys
import PySimpleGUI as sg
from pynput.keyboard import Key, Controller
import cv2
import boto3
import numpy as np
import os 
import s3fs
from PIL import Image


#Amanzon Rekognition collection name
collectionId='490bfaceid' 
#s3 bucket name
bucket_name = "indexed-faces490"
#init boto3 client
s3 = boto3.client('s3')
#init rekognition with keys
rekognition = boto3.client('rekognition',aws_access_key_id= '',
             aws_secret_access_key='',
             region_name='us-west-2')

#Spotify Dashboard Auth IDs and keys 
username = ''
clientID = ''
clientSecret = ''
redirectURI = 'http://localhost:8888/callback'

# Create OAuth Object
oauth_object = spotipy.SpotifyOAuth(clientID,clientSecret,redirectURI)
# Create token
token_dict = oauth_object.get_access_token()
token = token_dict['access_token']
# Create Spotify Object
spotifyObject = spotipy.Spotify(auth=token)
#This is my spotify account 
user = spotifyObject.current_user()

#Keyboard reroute for future touch screen + gui
command = Controller()
next_track = 'f'
previous_track = 'd'
start_of_track = 'b'
volume_up = '+'
volume_down = '-'
forward = '.'
rewind = ','
mp3quit = 'q'

#main function 
def main():
    #simple python gui for demonstration purposes 
    sg.theme('Light Teal')

    # define the window layout
    layout = [[sg.Text('Biometric Media Player', size=(30, 1), justification='left', font='TimesNewRoman 20')],
              [sg.Image(filename='', key='image')],
              [sg.Button('Capture', size=(10, 1), font='TimesNewRoman 14')]]

    # create the window and show it without the plot
    window = sg.Window('Facetunes', layout, location=(800, 400))
    #Open webcam
    cap = cv2.VideoCapture(0)

    # ---===--- Event LOOP Read and display frames, operate the GUI --- #
    while True:
        event, values = window.read(timeout=20)
        ret, test = cap.read()
        #live camera feed with update 
        imgbytes = cv2.imencode('.png', test)[1].tobytes() 
        window['image'].update(data=imgbytes)
        if event == 'Exit' or event == sg.WIN_CLOSED:
            return
        #gui button press camera capture 
        elif event == 'Capture':
            cv2.imwrite('/home/aaron/490bdemo/test.jpg',test)
            #rahdom indexing so photos dont get overwritten, kinda shitty implemenation but works for now
            i = random.randrange(99999999999)
            
            #AWS response code 
            #opens captured photo and saves image data as response content 
            with open('test.jpg', 'rb') as image_data:
                response_content = image_data.read()
            
            #rekognition detect faces takes response content data and sees if theres a face or not, client and script will crash if there is no faces detected
            rekognition_response = rekognition.detect_faces(Image={'Bytes':response_content}, Attributes=['ALL'])
            #match responses checks amazon collection and compares it to captured face photo which is your response content var 
            match_response = rekognition.search_faces_by_image(CollectionId=collectionId, Image={'Bytes': response_content}, MaxFaces=1, FaceMatchThreshold=85)
            image = Image.open('test.jpg')
            image_width, image_height = image.size

            #built in linux music player, mpg123 audio decoder, currently just changing os directories to play music 
            def playmusic():
                dominantMood = face_emotion
                if dominantMood == 'HAPPY':
                    os.chdir("Music")
                    os.chdir("Happy")
                    os.system("mpg123 -Z *.mp3")
                elif dominantMood == 'SAD':
                    os.chdir("Music")
                    os.chdir("Sad")
                    os.system("mpg123 -Z *.mp3")
                elif dominantMood == 'ANGRY':
                    os.chdir("Music")
                    os.chdir("Angry")
                    os.system("mpg123 *.mp3")
                elif dominantMood == 'FEAR':
                    os.chdir("Music")
                    os.chdir("Fear")
                    os.system("mpg123 *.mp3")
                elif dominantMood == 'SUPRISED':
                    os.chdir("Music")
                    os.chdir("Suprise")
                    os.system("mpg123 *.mp3")
                elif dominantMood == 'DISGUST':
                    os.chdir("Music")
                    os.chdir("Disgust")
                    os.system("mpg123 *.mp3")
                elif dominantMood == 'CALM':
                    os.chdir("Music")
                    os.chdir("Neutral")
                    os.system("mpg123 *.mp3")
            
            #function checks to see a folder existence in our s3 bucket, each folder contains user id and a facial picture of the user
            def folder_exists(bucket, path):
                #strip just so its easier to parse data 
                path = path.rstrip('/')
                resp = s3.list_objects(Bucket=bucket, Prefix=path, Delimiter='/',MaxKeys=1)
                return 'CommonPrefixes' in resp
           
           #simple for loop to create a cropped photo of bounding box, this is going to be the png uploaded to the s3 bucket
            for item in rekognition_response.get('FaceDetails'):
                bounding_box = item['BoundingBox']
                width = image_width * bounding_box['Width']
                height = image_height * bounding_box['Height']
                left = image_width * bounding_box['Left']
                top = image_height * bounding_box['Top']

                left = int(left)
                top = int(top)
                width = int(width) + left
                height = int(height) + top

                box = (left, top, width, height)
                box_string = (str(left), str(top), str(width), str(height))
                cropped_image = image.crop(box)
                thumbnail_name = '{}.png'.format(i)
                i += 1
                saved_imgs = cropped_image.save(thumbnail_name, 'PNG')

                face_emotion_confidence = 0
                face_emotion = None
            
            #printing highest confidence emotion state for demo purposes 
            for emotion in item.get('Emotions'):
                print(emotion)
                if emotion.get('Confidence') >= face_emotion_confidence:
                    face_emotion_confidence = emotion['Confidence']
                    face_emotion = emotion.get('Type')
             #print('user:{} your current emotion is {}'.format(match_response['FaceMatches'][0]['Face']['ExternalImageId'], face_emotion))
                    print("Current User your primary emotion is currently," + face_emotion)

                #prints similarity and confidence of face match and user if the confidence and similarity threshold is greater than 85
                if match_response['FaceMatches']:
                    print('Similarity:',match_response['FaceMatches'][0]['Similarity'])
                    print('Confidence:',match_response['FaceMatches'][0]['Face']['Confidence'])
                    print('Hello, user:',match_response['FaceMatches'][0]['Face']['ExternalImageId'])
                    playmusic()
                else:
                    print("No faces matched")
                    #user creation, psudeo data base honestly
                    #this is the upload of the user sign up photo thru s3 functions
                    print("Would you like to create a new user profile? (y/n)")
                    user_choice = input()
                    if user_choice == 'y':
                        print('please insert username')
                        username = input()
                        folder_name = str(username)
                        filepath = '/home/aaron/490bdemo/' + str(thumbnail_name)
                        dest_file_name = str(thumbnail_name)
                        all_objects = s3.list_objects(Bucket = bucket_name)
                        doseUserExist =folder_exists(bucket_name, folder_name)
                        
                        #checks if user name is already in our s3 bucket 
                        if doseUserExist:
                            print("This username has been taken please pick a different username")
                            print("Please restart the client and pick a new user name")
                            #add in a recursive function in future to prompt user to pick a new user name
                        else:
                            #uploads bounded box crop pic to aws s3 bucket
                            s3.put_object(Bucket=bucket_name, Key=(folder_name+'/'))
                            s3.upload_file(filepath,bucket_name, '%s/%s' % (folder_name,dest_file_name))
                        #create new user folder for music upload
                        #will have to write something to clone the tree structure of the init music folder
                        parent_dir = "/home/aaron/490bdemo"
                        src = "'home/aaron/490bdemo/temp"
                        directory = folder_name
                        path = os.path.join(parent_dir, directory)
                        os.chdir(parent_dir)
                        os.mkdir(path)
                        os.remove(filepath)

                        bucket = bucket_name
                        all_objects = s3.list_objects(Bucket =bucket )
                        list_response=rekognition.list_collections(MaxResults=2)

                        if collectionId in list_response['CollectionIds']:


                            rekognition.delete_collection(CollectionId=collectionId)


                        #create a new collection 

                        rekognition.create_collection(CollectionId=collectionId)


                        #add all images in current bucket to the collections
                        #use folder names as the labels


                        for content in all_objects['Contents']:
                            collection_name,collection_image =content['Key'].split('/')
                            if collection_image:
                                label = collection_name
                                print('indexing: ',label)
                                image = content['Key']    
                                index_response=rekognition.index_faces(CollectionId=collectionId,
                                                                    Image={'S3Object':{'Bucket':bucket,'Name':image}},
                                                                    ExternalImageId=label,
                                                                    MaxFaces=1,
                                                                    QualityFilter="AUTO",
                                                                    DetectionAttributes=['ALL'])
                                print('FaceId: ',index_response['FaceRecords'][0]['Face']['FaceId'])


                    #no user mode, plays music locally 
                    elif user_choice == 'n':
                        playmusic()
                    else:
                        print('Please pick either y/n')
                    return
                    
main()