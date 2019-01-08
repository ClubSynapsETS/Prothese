import json
import numpy as np
import tensorflow as tf

# importing myo communication utilities
from myo_read_raw.pipeline_buffer import launch_myo_comm, reset_pipeline_buff_flags

# importing data processing/pipeline utilities
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline

# importing model utilities
from snaprnn.evaluate import restore_tf_session, zero_padd_sequence

pipeline_buffer_size = 50
calibration_file = "Example_calibration_file.json"
model_dir = "Model/"

movement_names = {
    "0" : "hand_close",
    "1" : "hand_open",
    "2" : "index_close",
    "3" : "middle_finger_close",
    "4" : "thumb_close",
    "5" : "ring_finger_close",
    "6" : "pinky_finger_close"
}

if __name__ == "__main__":

    # starting the buffer maintenance process
    r_server, buffer_maintenance_p = launch_myo_comm(pipeline_buffer_size)

    # defining the calibration pipeline
    cal_pipeline = get_calibration_Pipeline(calibration_file)

    # fetching the session where the model was defined
    restored_sess, _ = restore_tf_session(model_dir)
    
    # using the restored model session
    with restored_sess as session:

        # fetching the necessary operations and place holders for training
        X = tf.get_collection('X')[0]
        seq_length = tf.get_collection('seq_length')[0]
        training_model = tf.get_collection('training_model')[0]
        logits_op = tf.get_collection('logits_op')[0]
        predictions_op = tf.get_collection('class_ids')[0]
        prob_op = tf.get_collection('probabilities')[0]

        # pulling model input dimensions
        n_inputs = int(X.shape[2])
        n_steps = int(X.shape[1])

        # defining input container for the model
        movement_data = np.zeros((0, n_inputs))
        movement_len = 0

        try:

            # while the incoming buffer is maintained
            while(r_server.get("buffer_maintained") == "1"):
                
                # pipeline buffer is ready to be read
                if(r_server.get("buffer_ready") == "1"):

                    # adding to the movement length
                    movement_len += 1

                    # adding buffer content to the movement data
                    pipeline_buff = np.array(json.loads(r_server.get("pipeline_buff")))
                    pipeline_buff = cal_pipeline.fit_transform(pipeline_buff)
                    movement_data = np.vstack([movement_data, 
                                    np.reshape(pipeline_buff, n_inputs)])
                    
                    # data can be received
                    reset_pipeline_buff_flags(r_server)

                    # formatting the movement data
                    formatted_mov = zero_padd_sequence(movement_data, n_steps)
                    formatted_mov = np.expand_dims(formatted_mov, axis=0)

                    # formatting the curr movement length
                    formatted_seq_len = np.array([movement_len])

                    # evaluating the model with the movement data
                    probabilities = session.run(prob_op, 
                                    feed_dict={training_model:False, seq_length:formatted_seq_len, X:formatted_mov})
                    predictions = session.run(predictions_op, 
                                    feed_dict={training_model:False, seq_length:formatted_seq_len, X:formatted_mov})

                    # pairing the prediction and the probability
                    curr_step_pred = predictions[0][movement_len-1]
                    current_prob = probabilities[0][movement_len-1][curr_step_pred]
                    print(movement_names[str(curr_step_pred)], " - ", str(current_prob), " - ", str(movement_len), "\n")

                    # managing the size of the movement
                    if movement_len >= n_steps:
                        movement_data = np.zeros((0, n_inputs))
                        movement_len = 0
        
        except:
            # unsetting continuation flag for the child process
            r_server.set("incoming_data", "0")

    # waiting for the child process to end
    buffer_maintenance_p.join()