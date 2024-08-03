from flask import Flask, render_template, request, jsonify
from RouteFinder import RouteFinder
import traceback
import os
from creds.constants import User

app = Flask(__name__)
routeFinder = RouteFinder()
routeFinder.populateCosts()

progress = 0

success = None

# Ensure the Data directory exists
os.makedirs('Data', exist_ok=True)

@app.route("/", methods=['GET', 'POST'])
def home():
    global success
    success = None
    routeFinder.update_progress(0, "restart")
    routeFinder.setAttemptCounter(1)
    sourceNodes, destinationNodes, hotelStars = routeFinder.getDataFromDB()
    
    # Initialize an empty dictionary to store grouped data
    hotels = {}
    
    # Iterate through the original dictionary
    for hotel, stars in hotelStars.items():
        if stars not in hotels:
            hotels[stars] = {}  # Initialize dictionary if key doesn't exist
        hotels[stars][hotel] = destinationNodes[hotel]  # Add hotel name with its node number
    
    hotels = dict(sorted(hotels.items(), reverse=True))  # Sort the dictionary by key in descending order
    sourceNodes = dict(sorted(sourceNodes.items()))  # Sort the dictionary by key in ascending order
    
    if request.method == 'POST':
        selected_pickup_node = request.form.get('pickupPoint')
        selected_hotel_names = request.form.getlist('hotels')
        selected_routes = request.form.getlist('routeType')
        
        # Get the selected pickup point's name
        selected_pickup = next((name for name, node in sourceNodes.items() if node == int(selected_pickup_node)), None)
        
        # Get the names of the selected hotels
        selected_hotels = [name for name, node in destinationNodes.items() if str(name) in selected_hotel_names]
        
        try:
            while success == None and routeFinder.getAttemptCounter() < 4:
                print(f"\n---THIS IS ATTEMPT #{routeFinder.getAttemptCounter()}---\n")
                success = routeFinder.flow2(selected_pickup, selected_hotels, selected_routes)
                if not success:
                    success = None
                    routeFinder.setAttemptCounter(routeFinder.getAttemptCounter() + 1)
            
            if success == False:
                return jsonify({'success': False, 'message': 'Failed to Generate Routes. Please try again.'})
        
        except Exception as e:
            success = False
            error_line = traceback.format_exc().splitlines()[-1]
            print(f"---ERROR---: {error_line}")
            return jsonify({'success': False, 'error': str(e), 'message': f'Failed to Generate Routes. Error: {error_line}'})
        
        else:
            if success == True:
                return jsonify({'success': True, 'message': 'Routes Generated Successfully.'})
    
    return render_template('index.html', terminals=sourceNodes, hotels=hotels, showResult=False, user=User)

@app.route('/progress')
def get_progress():
    try:
        progress = routeFinder.get_progress()
        response = jsonify({'result': success, 'progress': progress})
        return response
    except Exception as e:
        error_details = traceback.format_exc()
        print(error_details)  # Log the full traceback
        return jsonify({'result': success, 'error': str(e), 'progress': 0}), 500


@app.route('/result')
def result():
    return jsonify(routeFinder.get_results())

@app.route("/route")
def route():
    weight = request.args.get('weight', 'combined')
    
    base_url = f'https://storage.googleapis.com/dsaproject-ac038.appspot.com/maps/{User}optimalRoute'
    
    if weight in ['length', 'time', 'erp']:
        map_url = f'{base_url}_{weight}.html'
    else:
        map_url = f'{base_url}.html'
    
    return render_template('mapDisplay.html', map=map_url)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global routeFinder
    if request.method == 'POST':
        update_db_status = request.form.get('updateDBStatus') == 'Yes'
        check_traffic_status = request.form.get('checkTrafficStatus') == 'Yes'
        
        routeFinder = RouteFinder(update=update_db_status, traffic=check_traffic_status)
        routeFinder.populateCosts()
        
        # Handle file upload
        file = request.files.get('fileUploadERP')
        if file and file.filename.endswith('.geojson'):
            filename = 'default.geojson'  # The uploaded file will overwrite the default.geojson file
            file_path = os.path.join('Data', filename)
            file.save(file_path)
            print(f"File saved to {file_path} successfully.")
        
        print("Settings Updated Successfully.")
        return jsonify(success=True)
    
    return render_template('settings.html', updateDBStatus=routeFinder.getUpdateDBStatus(), checkTrafficStatus = routeFinder.getCheckTrafficStatus())


if __name__ == "__main__":
    app.run(debug=True)
