import os
import shutil

from classifier_jk import add_face_to_known, classify_image, initalize

# If the folder already exists, delete it for testing
if os.path.exists("./PeopleKnown/Lewandowski"):
    shutil.rmtree("./PeopleKnown/Lewandowski", ignore_errors=True)

# Initalize the already known images
initalize()

classify_image("./PeopleUnknown/Lewandowski_Test.jpeg")

add_face_to_known("./PeopleUnknown/Lewandowski_1.jpeg", "Lewandowski")
add_face_to_known("./PeopleUnknown/Lewandowski_2.jpeg", "Lewandowski")
add_face_to_known("./PeopleUnknown/Lewandowski_3.jpeg", "Lewandowski")
add_face_to_known("./PeopleUnknown/Lewandowski_4.jpeg", "Lewandowski")
add_face_to_known("./PeopleUnknown/Lewandowski_5.jpeg", "Lewandowski")
add_face_to_known("./PeopleUnknown/Lewandowski_6.jpeg", "Lewandowski")

classify_image("./PeopleUnknown/Lewandowski_Test.jpeg")
