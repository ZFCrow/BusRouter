function updateHotelsDropdown(selectedStarRatings) {
    const hotelsDropdown = $('#hotels-dropdown');
    hotelsDropdown.empty();  // Clear current options
    
    selectedStarRatings.forEach(starRating => {
        const hotelsList = hotelsData[starRating];
        if (hotelsList) {
            Object.entries(hotelsList).forEach(([name, node]) => {
                const stars = '⭐'.repeat(parseInt(starRating));
                const optionText = `${name} (${stars})`;
                const option = new Option(optionText, name);
                hotelsDropdown.append(option);
            });
        }
    });
    
    // Sort the dropdown options by name
    hotelsDropdown.find('option').sort(function (a, b) {
        return a.text.localeCompare(b.text);
    }).appendTo(hotelsDropdown);
    
    hotelsDropdown.trigger('change');  // Refresh the dropdown
}

function showConfirmation() {
    const pickupPoint = document.querySelector('#pickupPoint');
    const selectedPickup = pickupPoint.options[pickupPoint.selectedIndex].text;
    
    const selectedHotels = Array.from(document.getElementById('hotels-dropdown').selectedOptions).map(option => option.text);
    const selectedRouteTypes = Array.from(document.querySelectorAll('input[name="routeType"]:checked')).map(input => input.nextElementSibling.innerText);
    
    document.getElementById('modalPickupPoint').innerText = selectedPickup !== 'Select an Airport Terminal' ? selectedPickup : 'None';
    document.getElementById('modalHotels').innerText = selectedHotels.length > 0 ? selectedHotels.join(', ') : 'None';
    document.getElementById('modalRoutes').innerText = selectedRouteTypes.length > 0 ? selectedRouteTypes.join(', ') : 'None';
    
    // No pickup point selected
    if (selectedPickup == 'Select an Airport Terminal') {
        alert('Please select a pickup point!');
        return;
    }
    
    // No hotels selected
    if (selectedHotels.length == 0) {
        alert('Please select at least one hotel.');
        return;
    }
    
    // No route type selected
    if (selectedRouteTypes.length == 0) {
        alert('Please select at least one route type.');
        return;
    }
    
    // Allowing user to confirm selection only if both pickup point and hotels are selected
    else {
        const modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
        modal.show();
    }
}

function submitForm() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('confirmationModal'));
    modal.hide();
    
    // Show progress bar
    document.getElementById('progressBarContainer').style.display = 'block';
    updateProgressBar(10);  // Reset progress bar
    
    // Serialize form data
    const formData = $('#routeForm').serialize();
    
    startProgressPolling();
    
    $.ajax({
        type: 'POST',
        url: '/',
        data: formData,
        success: function (response) {
            console.log('Form Submission Result:', response);
            if (response.success) {
                document.getElementById('routeResult').textContent = response.message;
                document.getElementById('routeResult').style.color = 'green';
            } 
            
            if (response.success == false) {
                document.getElementById('routeResult').textContent = response.message;
                document.getElementById('routeResult').style.color = 'red';
            }
        },
        error: function (error) {
            console.error('Error submitting form:', error);
            document.getElementById('routeResult').textContent = 'An error occurred. Please try again.';
            document.getElementById('routeResult').style.color = 'red';
        }
    });
}

function updateProgressBar(percent) {
    const progressBar = document.getElementById('progressBar');
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    progressBar.innerHTML = `<h6>Generating Routes... ${percent}% Complete</h6>`;
}

function startProgressPolling() {
    const interval = setInterval(() => {
        fetch('/progress')
            .then(response => response.json())
            .then(data => {
                console.log('Progress:', data.progress);
                console.log('Result:', data.result)
                updateProgressBar(data.progress);
                if(data.result === false) {
                    clearInterval(interval);
                    // Hide progress bar
                    document.getElementById('progressBarContainer').style.display = 'none';
                    console.error('Server returned an error:', data.error);
                }
                
                if (data.progress >= 100) {
                    clearInterval(interval);
                    getRouteResult();
                }
            })
            .catch(error => {
                console.error('Error fetching progress:', error);
            });
    }, 500);  // Update every 0.5 seconds
}

function getRouteResult() {
    fetch('/result')
        .then(response => response.json())
        .then(data => {
            console.log('Route data:', data);
            updateResultContainer(data);
            document.querySelector('.resultContainer').style.display = 'block';  // Show result container'
            
            document.getElementById('progressBarContainer').style.display = 'none'; // Hide progress bar
        })
        .catch(error => console.error('Error fetching route data:', error));
}

function updateResultContainer(results) {
    const weightTypes = results.selectedWeights;
    const cardsContainer = document.getElementById('cardsContainer');
    cardsContainer.innerHTML = '';

    weightTypes.forEach(weight => {
            cardsContainer.innerHTML += createCard(weight);
        });
    
    weightTypes.forEach(weight => {
        const sourceText = `Source: ${results.source}`;
        const destinationsText = `Destinations: ${results.destinations.join(', ')}`;
        const costText = weight === 'length' ? `Total Distance: ${results[`${weight}Cost`]}` :
                            weight === 'time' ? `Time Taken: ${results[`${weight}Cost`]}` :
                            `ERP Cost: ${results[`${weight}Cost`]}`;
        const alternateCostText = `Alternate Costs: ${results[`${weight}AlternateCost`]}`;
        const optimalRoute = results[`optimalPath_${weight}`];
        const optimalRouteDirections = results[`optimalRouteInstructions_${weight}`];
        
        document.getElementById(`optimalRoute_${weight}`).src = document.getElementById(`optimalRoute_${weight}`).src;
        document.querySelector(`.card-${weight} .card-text.source-text`).textContent = sourceText;
        document.querySelector(`.card-${weight} .card-text.destination-text`).textContent = destinationsText;
        document.querySelector(`.card-${weight} .card-text.costs-text`).textContent = costText;
        document.querySelector(`.card-${weight} .card-text.alternate-costs-text`).innerHTML = alternateCostText;
        document.querySelector(`.card-${weight} .card-text.optimal-route`).textContent = optimalRoute;
        document.querySelector(`.card-${weight} .card-text.${weight}-route-instructions`).innerHTML = optimalRouteDirections;
    });
    
    reloadEmbed(results.selectedWeights);
}

function createCard(weight) {
    const weightTitles = {
        length: 'Shortest Route (Length)',
        time: 'Fastest Route (Time)',
        erp: 'Traffic Route (ERP)'
    };
    
    return `
        <div class="col-md-6" id="${weight}Card" style="margin-top: 30px;">
            <div class="card card-${weight}">
                <div class="card-header">
                    <h5>${weightTitles[weight]}</h5>
                </div>
                <div class="card-body">
                    <embed id="optimalRoute_${weight}" type="text/html"
                        src="https://storage.googleapis.com/dsaproject-ac038.appspot.com/maps/${user}optimalRoute_${weight}.html"
                        style="width: 100%; height: 100%;" />
                    <p class="card-text source-text">Source:</p>
                    <p class="card-text destination-text">Destinations:</p>
                    <p class="card-text costs-text"></p>
                    <div class="card-text alternate-costs-text"></div>
                    <p class="card-text optimal-route"></p>
                    <button class="btn btn-primary" onclick="openMap('${weight}')">Open Map in New Tab</button>
                    <button class="btn btn-info" onclick="showInstructions('${weight}')">Show/Hide Driving Directions</button>
                    <div class="card-text ${weight}-route-instructions" style="display:none; margin-top: 30px;"></div>
                </div>
            </div>
        </div>
        `;
}


function openMap(weight) {
    var timestamp = new Date().getTime();  // Get current timestamp
    window.open(`/route?weight=${weight}&t=${timestamp}`, '_blank'); // Open map in new tab with current timestamp
}

function showInstructions(weight) {
    const instructionsSelector = `.card-text.${weight}-route-instructions`;
    const instructionsElement = document.querySelector(instructionsSelector);
    
    if (instructionsElement.style.display === 'none' || instructionsElement.style.display === '') {
        instructionsElement.style.display = 'block';
    } 
    else {
        instructionsElement.style.display = 'none';
    }
}

function updateSettings() {
    var formData = new FormData(document.getElementById('settingsForm'));
    formData.append('updateDBStatus', document.querySelector('input[name="updateDBOptions"]:checked').value);
    formData.append('checkTrafficStatus', document.querySelector('input[name="updateTrafficOptions"]:checked').value);
    
    document.getElementById('updateSettingsResult').style.display = 'block';
    document.getElementById('updateSettingsResult').style.color = 'red';
    document.getElementById('updateSettingsResult').textContent = "Updating Settings, Please wait...";
    
    $.ajax({
        url: '/settings',
        type: 'POST',
        processData: false,
        contentType: false,
        data: formData,
        success: function(response) {
            if (response.success) {
                document.getElementById('updateSettingsResult').style.color = 'green';
                document.getElementById('updateSettingsResult').textContent = "Settings Updated Successfully!";
            } else {
                document.getElementById('updateSettingsResult').style.color = 'red';
                document.getElementById('updateSettingsResult').textContent = "Error updating settings.";
            }
        }
    });
}

function reloadEmbed(selectedWeights) {
    for (var i = 0; i < selectedWeights.length; i++) {
        var embedId = `optimalRoute_${selectedWeights[i]}`;
        var embedElement = document.getElementById(embedId);
        var originalSrc = embedElement.src.split('?')[0]; // Removes any existing query string
        var timestamp = new Date().getTime(); // Unique timestamp to force reload
        embedElement.src = `${originalSrc}?t=${timestamp}`;
    }
}

function toggleDarkMode() {
    const wasDarkMode = localStorage.getItem('darkMode') === 'true';
    localStorage.setItem('darkMode', !wasDarkMode);
    const element = document.body;
    element.classList.toggle('darkMode', !wasDarkMode);
    document.getElementById('darkModeToggle').checked = !wasDarkMode;
}

function onload() {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('darkMode');
    } else {
        document.body.classList.remove('darkMode');
    }
    
    document.getElementById('darkModeToggle').checked = isDarkMode;
}


$(document).ready(function () {
    $('#stars-dropdown').select2({
        placeholder: "Select Star Ratings",
        allowClear: true,
    }).on('change', function () {
        const selectedStarRatings = $(this).val() || [];
        updateHotelsDropdown(selectedStarRatings);
    });
    
    $('#hotels-dropdown').select2({
        placeholder: "Select a Destination",
        allowClear: true,
        multiple: true,
        tags: true
    });
    
    // Default to 5-star hotels in the dropdown
    const defaultRatings = $('#stars-dropdown').val() || [];
    updateHotelsDropdown(defaultRatings);
});