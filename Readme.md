For The API Aspect of my code

The @app.put("/settings") function
-Basically allows the useer to set the temperature threshold, the light activation time and the period th light will remain on.

The @app.get("/control")  function
- Basically controls wheter the fan and light should be turned on or not based on the sensor readings recieved.

The  @app.get("/graph") function
-This basically collects the most recents sensor value and displays it via a graph.

For the Embedded Code

-It basically connets to the wifi, then reads the temperature and searches if there is presence detected or not and then sends the sensory value recieved and sends it to the FastAPI along with the current time to the /control endpoint and then repeats the controlling cycle.