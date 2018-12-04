#include "finger_interface.h"

// shared data structure for BT
extern volatile bt_shared_data_t bt_shared_buffer;

static const char* ACT_TASK = "ACTUATOR IFACE";
static esp_adc_cal_characteristics_t *adc_chars;

static actuator_instruct_t pq12_charact = 
{
    .set_time = 0, .set_speed = 0, .direction = 0,
    .max_speed = 28 //in mm/s
};

//finger object initilisation
static finger_charc_t xfingerCharac[4] =
{
    //Index charactheristic and componants
    { .finger_id=index0, .state=FG_SET_POS, .last_set_pos=10, .cur_position=0,
        .act=&pq12_charact, .adc_channel=ADC1_CHANNEL_0, 
        .lower_gpio=GPIO_NUM_32, .upper_gpio=GPIO_NUM_33,
        .max_position=18.83, .min_position=5.46, .time_stamp=0 
    },
    //Majeur
    { .finger_id=majeur1, .state=FG_SET_POS, .last_set_pos=10, .cur_position=0,
        .act=&pq12_charact, .adc_channel=ADC1_CHANNEL_3, 
        .lower_gpio=GPIO_NUM_25, .upper_gpio=GPIO_NUM_26,
        .max_position=18.83, .min_position=5.46, .time_stamp=0 
    }, 
    //Anulaire
    { .finger_id=anulaire2, .state=FG_SET_POS, .last_set_pos=10, .cur_position=0,
        .act=&pq12_charact, .adc_channel=ADC1_CHANNEL_6, 
        .lower_gpio=GPIO_NUM_14, .upper_gpio=GPIO_NUM_27,
        .max_position=16.343, .min_position=2.873, .time_stamp=0 
    }, 
    //Auricualire
    { .finger_id=auriculaire3, .state=FG_SET_POS, .last_set_pos=10, .cur_position=0,
        .act=&pq12_charact, .adc_channel=ADC1_CHANNEL_7, 
        .lower_gpio=GPIO_NUM_12, .upper_gpio=GPIO_NUM_13,
        //hardcoded max and min position
        .max_position=19.28, .min_position=4.804, .time_stamp=0 
    } 
};


/*Module main finger interface*/
void vFingerInterface( void * pvParam )
{
    double instruction[4] = {0};
  
    // calibrating the ADC1
    adc_chars = calloc(1, sizeof(esp_adc_cal_characteristics_t));
    esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);
    adc1_config_width(ADC_WIDTH_BIT_12);

    int each_fg;
    for(each_fg=0; each_fg<=3; each_fg++) {

        //Configure ESP32 outputs
        config_actuator_channel(&xfingerCharac[each_fg]);
        
        //for each finger create a timer subroutine
        char timer_name[13] = "finger_timer ";
        timer_name[12] = '0'+each_fg; //append number to name "finger1, finger2"
        ESP_LOGI(ACT_TASK, "Creating %s .", timer_name);
        esp_timer_create_args_t actuator_timer_args = {
            .callback = &actuator_timer_callback,
            .arg = (void*) &xfingerCharac[each_fg], //This one is unavoidable, we need a ptr here.
            /* name is optional, but may help identify the timer when debugging */
            .name = timer_name
        };
        //create timer and store handler inside finger charc struct
        esp_timer_create(&actuator_timer_args, &xfingerCharac[each_fg].timer_handle);
    }

    for(;;)
    {
        
        // logging task activity
        ESP_LOGI(ACT_TASK,"");

        if(bt_shared_buffer.data_read == 0){

            // converting the received myo pose to instructions
            pose_to_finger_instructs(instruction, N_FINGERS, bt_shared_buffer.myo_pose);
            bt_shared_buffer.data_read = 1;

            //Main interfacen, get state, compare to instructions, act upon a difference between the two of them. 
            for(each_fg=0; each_fg<=3; each_fg++) {

                xfingerCharac[each_fg].state = actuator_state( &xfingerCharac[each_fg]);

                //if an action is required...
                if(finger_mouvement_planing( &xfingerCharac[each_fg], instruction[each_fg] ) == 1 ){
                    finger_control_iface(&xfingerCharac[each_fg]);
                }
                
            }
        }

        //TODO: Stalling callback
        /* E) Staling detection task to ISR
         * To save processing time, adc reads will not happen when the finger is either closed or opened.
         * This task will remember the last two value and compare it to the most recent one
         * When detected, call upon an CPU interrupt (hold give) to make the finger interface react accordingly.
         * https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/system/intr_alloc.html
         */

        //TODO: multiple ways to enter this task, semaphore + queues
        //If the task can take the semaphore it means one or more actuator is stalling.
        //A variable (stalling_finger) will contain which one called the interface.
        /*xSemaphoreTake(xSemapStalling, 3);*/

        /* F) Shutting down actuator subrotine
         * function call when either stalling is detected or not required. 
         *  1. Stop actuator, both GPIO pulled down
         *  2. Change interface finger state.
         */

        vTaskDelay(pdMS_TO_TICKS(200));

    }

    // deleting the current task
    // this should not happen
    vTaskDelete(NULL);
}


// converts pose data from the myo to instructions for the fingers
// the provided array gets updated with the instructions corresponding to "pose"
// Instructions :
//    - array where each member = the contraction (percentage) for a finger
//    - instruction[0]=Index instruction[1]=Majeur, instruction[2]=Anulaire, instruction[3]=Auricualire
void pose_to_finger_instructs(double* instruction, int len, int pose){

    double instruction_val = 0;
    int iter;

    switch(pose){
        case FIST:
            instruction_val = INSTRUCT_FG_CLOSE;
            ESP_LOGI(ACT_TASK, "Received : FIST Pose"); 
        break;
        case FINGERS_SPREAD:
            instruction_val = INSTRUCT_FG_OPEN; 
            ESP_LOGI(ACT_TASK, "Received : FINGERS_SPREAD Pose"); 
        break; 
        case REST:
            instruction_val = INSTRUCT_FG_OPEN;
            ESP_LOGI(ACT_TASK, "Received : REST Pose"); 
        break;
    }

    for(iter=0; iter<len; iter++) {
        instruction[iter] = instruction_val;
    }

}


// Configures the hardware/pins for a specdified actuator.
void config_actuator_channel(finger_charc_t * fg)
{
    //Configure ADC
    adc1_config_channel_atten(fg->adc_channel, ADC_ATTEN_DB_11);

    //configure GPIO channels
    gpio_config_t io_conf;
    io_conf.intr_type = GPIO_PIN_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = ((1ULL<<fg->upper_gpio) | (1ULL<<fg->lower_gpio));
    io_conf.pull_down_en = 0;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);

    //set pin level to low
    gpio_set_level(fg->upper_gpio, 0);
    gpio_set_level(fg->lower_gpio, 0);
}


// returns averaged adc value for the specified chanel 
uint32_t Actuator_Pos_volt(adc1_channel_t channel)
{
    //TODO: optimise this subroutine, is currently take 1300us
    const uint8_t no_samples = 32;
    uint32_t voltage;
    uint32_t adc_reading = 0;
    int i;
    //Multisampling of adc channel, to reduce inaccuracy.
    for (i = 0; i < no_samples; i++) 
        adc_reading += adc1_get_raw(channel);
    
    adc_reading /= no_samples;
    //Convert adc_reading to voltage in mV
    voltage = esp_adc_cal_raw_to_voltage(adc_reading, adc_chars);

    return voltage;
}


fg_state_e actuator_state(finger_charc_t * fg)
{
    const double mVtomm_slope = -0.006255481443114;
    uint64_t timestamp[3];
    double delta_time;
    double positions[3], cur_position=0, delta_x;
    double total_speed=0, speeds[2];
    uint32_t mVolt;
    
    //Get samples and timestamps, convert them from mV to mm
    int num_sample, calc;
    for(num_sample=0; num_sample<3; ++num_sample) {
        cur_position=0;
        timestamp[num_sample] = esp_timer_get_time();
        mVolt = Actuator_Pos_volt(fg->adc_channel);
        if(num_sample ==2)
        //x = mv * slope + b
        cur_position = mVtomm_slope * (double)mVolt;
        cur_position +=20;
        if(cur_position <0) cur_position =0;

        positions[num_sample] = cur_position;
    }
    fg->cur_position = positions[2];
    ESP_LOGI(ACT_TASK, "finger%d", (int)fg->finger_id);
    ESP_LOGI(ACT_TASK, "positions, 0:%f, 1:%f, 2:%f", positions[0], positions[1], positions[2]);

    //Calculate speeds
    for(calc=0; calc<2; ++calc) {
        delta_time = (double)(timestamp[calc+1] - timestamp[calc]);
        delta_time /= 1000; //Convert us to ms
        delta_x = positions[calc+1] - positions[calc];
        speeds[calc] = delta_x/delta_time;
        total_speed += speeds[calc];
    }
    total_speed /= calc; //speed in mm/ms
    total_speed *= 10; //convert mm/ms -> mm/s
    ESP_LOGI(ACT_TASK, "Speed = %f", total_speed);

    ////State guesing logic
    
    //we're definatly moving
    if((total_speed > 4 || total_speed < -4) &&
          (total_speed < 29 || total_speed > -29)  ) {
        if(total_speed >0) return FG_OPENING;
        if(total_speed <0) return FG_CLOSING;
        ESP_LOGI(ACT_TASK, "efinger%d is moving at ludicris speed %f.", (int)fg->finger_id, total_speed );
    }

    //We've almost completly stopped moving
    else if(total_speed < 4 && total_speed > -4){

        ESP_LOGI(ACT_TASK, "efinger%d is not moving.", (int)fg->finger_id );
        
        // actuator is stoped at an extremity
        if(fg->cur_position >= (fg->max_position - 0.2) 
               && fg->cur_position <= (fg->max_position + 0.1)){
            return FG_OPENED;
        }
        else if(fg->cur_position <= (fg->min_position + 0.2) 
               && fg->cur_position >= (fg->min_position - 0.1)) {
            return FG_CLOSED;
        }

        // actuator is stoped in valid range
        else if(fg->cur_position > (fg->last_set_pos - 0.1) 
               && fg->cur_position < (fg->last_set_pos + 0.1)) {
            return FG_SET_POS;
        }
        
        //were not moving and were not at any valid position, nothing special to do.
        else {
            ESP_LOGW(ACT_TASK, "Wrong Position of actuator = %f", total_speed );
            return FG_INVALID;
        }

        //add overshoot detection logic and correction here
    }

    //Not going at any valid speed, something must be slowing the finger down.
    else {
        ESP_LOGE(ACT_TASK, "Finger%d's sensors have picked up something weird!", (int)fg->finger_id );
        ESP_LOGE(ACT_TASK, "Speed of actuator = %f", total_speed );
        return FG_WEIRD;
    }

    return FG_WEIRD;

}


//modeling module
int finger_mouvement_planing(finger_charc_t * fg, double toplvl_instruct)
{
    double delta_x;
    uint32_t time_to_target;

   //default do nothing.
   fg->act->set_speed = fg->act->max_speed;
   fg->act->set_time = 0;
   fg->act->direction = DIR_NONE;
   
   //Instruction is to set to max position but the finger is already there.
   if(INSTRUCT_FG_OPEN == toplvl_instruct && fg->state == FG_OPENED)
       return 0;

   //Instruction is to set to min position but the finger is already there.
   if(INSTRUCT_FG_CLOSE == toplvl_instruct && fg->state == FG_CLOSED)
       return 0;

   //convert instruction to an actual position
   double target_position = fg->min_position +((fg->max_position - fg->min_position)*toplvl_instruct);
   
   //Instruction is to set to a set position but the finger is already there.
   //very close to target position 
   if(fg->cur_position >= target_position-0.1 && fg->cur_position <= target_position+0.1
           && fg->state == FG_SET_POS) {
       return 0;
   }

   delta_x = target_position - fg->cur_position;
   ESP_LOGI(ACT_TASK, "MOVING TO POSITION %f from %f", target_position, fg->cur_position);

   //Insert speed modulation here. 
   //Top level instruction will have a force and timing add to it, that will be used to calculate the speed.
   fg->act->set_speed = fg->act->max_speed;
   
   //Finger will close
   if(delta_x < 0) {
       fg->act->direction = DIR_CONTRACT;
       delta_x *= -1; //time should be positive
       time_to_target = (uint64_t)((delta_x / fg->act->set_speed)*1000000); //time to reach in us
   
       //Last we checked, that finger was moving in wrong direction, we need to compensate
       //this needs to be smarter.
       if(fg->state == FG_OPENING)
           fg->act->set_time = time_to_target * 1.2;
       else
           fg->act->set_time = time_to_target;
   }
   //finger will open
   else {
       fg->act->direction = DIR_EXTEND;
       time_to_target = (uint64_t)((delta_x / fg->act->set_speed)*1000000); //time to reach in us

       //Last we checked, that finger was moving in wrong direction, we need to compensate
       //this needs to be smarter.
       if(fg->state == FG_CLOSING)
           fg->act->set_time = time_to_target * 1.2;
       else
           fg->act->set_time = time_to_target;
   }
   
   // logging new movement direction
   char * dir; 
   if(fg->act->direction == DIR_EXTEND)
       dir = "Extend";
   else
       dir = "Contract";
   ESP_LOGI(ACT_TASK, "pusle width = %d, direction = %s", time_to_target, dir);
    
    
   //remember for next iteration
   fg->last_set_pos = target_position;

   return 1;
    
}


//timer callback, so that we can forget the pulse until needed again.
void actuator_timer_callback(void* arg)
{
    finger_charc_t * fg = (finger_charc_t*)arg;

    gpio_set_level(fg->lower_gpio, 0);
    gpio_set_level(fg->upper_gpio, 0);
}


//control module
void finger_control_iface(finger_charc_t * fg)
{
    /* index    io  32 and 33
     * Majeur   io  25 and 26
     * Anulaire io  14 and 27 
     * Auriculaire io 12 and 13
     * When the lower (32,25,14,12) pin is high and the other one is low the actuator contracts
     * and vice-versa. 
     */
     if(fg->act->set_speed == fg->act->max_speed){
         if(fg->act->direction == DIR_CONTRACT){
             gpio_set_level(fg->lower_gpio, 1);
             gpio_set_level(fg->upper_gpio, 0);
         }
         else if(fg->act->direction == DIR_EXTEND) {
             gpio_set_level(fg->lower_gpio, 0);
             gpio_set_level(fg->upper_gpio, 1);
         }
         //pulse width, will handle the lowering of the channel.
         esp_timer_stop(fg->timer_handle); //Overwrite the last action if it is still in action.
         esp_timer_start_once(fg->timer_handle, fg->act->set_time);
     }
     
     else {
         //TODO: Define speed control scheme.
     }

}

