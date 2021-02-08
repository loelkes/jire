from jire import app, manager, csrf
from flask import request, render_template, redirect, url_for, jsonify, flash
from flask_api import status
from .CustomExceptions import ConferenceExists, ConferenceNotAllowed
from .forms import ReservationForm


@app.route('/conferences', methods=['GET'])
def show_conferences():
    return render_template('conferences.html',
                           conferences=manager.all_conferences)


@app.route('/')
@app.route('/reservations')
def home():
    form = ReservationForm()
    return render_template('reservations.html',
                           form=form,
                           reservations=manager.all_reservations)


@app.route('/reservation/create', methods=['POST'])
def reservation():
    form = ReservationForm()
    if form.validate_on_submit():
        data = form.data
        data['duration'] *= 60  # Convert minutes to seconds
        manager.add_reservation(data)
        app.logger.info('New reservation validation successfull')
        return redirect(url_for('home'))
    else:
        app.logger.info('New reservation validation failed')
        for key, value in form.errors.items():
            label = getattr(form, key).label.text
            # In case multiple messages for one validation?
            flash('{}: {}'.format(label, ' '.join([str(m) for m in value])), 'danger')
        return render_template('reservations.html',
                               form=form,
                               reservations=manager.all_reservations)


@app.route('/reservation/delete/<id>', methods=['GET'])
def delete_reservation(id):
    manager.delete_reservation(id=id)
    return redirect(url_for('home'))


@app.route('/conference', methods=['POST'])
@csrf.exempt
def conference():

    try:
        # If a user enters the conference, check for reservations
        output = manager.allocate(request.form)
    except ConferenceExists as e:
        # Conference already exists
        return jsonify({'conflict_id': e.id}), status.HTTP_409_CONFLICT
    except ConferenceNotAllowed as e:
        # Confernce cannot be created: user not allowed or conference has not started
        return jsonify({'message': e.message}), status.HTTP_403_FORBIDDEN
    else:
        return jsonify(output), status.HTTP_200_OK


@app.route('/conference/<id>', methods=['GET', 'DELETE'])
@csrf.exempt
def conference_id(id):

    if request.method == 'GET':
        # In case of 409 CONFLICT Jitsi will request information about the conference
        return jsonify(manager.get_conference(id).get_jicofo_api_dict()), status.HTTP_200_OK
    elif request.method == 'DELETE':
        # Delete the conference after it's over
        if manager.delete_conference(id=id):
            return jsonify({'status': 'OK'}), status.HTTP_200_OK
        else:
            return jsonify({
                'status': 'Failed',
                'message': f'Could not remove {id} from database.'
                }), status.HTTP_403_FORBIDDEN
