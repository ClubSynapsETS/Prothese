
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_timer.h"


#include <stdint.h>

//TODO: define actutor charc
static const actuator_t pq12_charact
{
    max_speed = 28; //in mm/s
}

//TODO : finger charc
static finger_charc_t xfingerCharac[4] =
{
    { efinger0, pq12_charact, ADC1_CHANNEL_0, {0,0}, 0 },
    { efinger1, pq12_charact, ADC1_CHANNEL_3, {0,0}, 0 },
    { efinger2, pq12_charact, ADC1_CHANNEL_6, {0,0}, 0 },
    { efinger3, pq12_charact, ADC1_CHANNEL_7, {0,0}, 0 }
};


//Modeling
/*void */


static finger_e stalling_finger;


/*Module main finger interface*/
void vFingerInterface( void * pvParam )
{
BaseType_t xStatus;
QueueHandle_t xFingerQueue, xTopLevelQueue;
SemaphoreHandle_t xSemapStalling


    //TODO instance of finger objects
    for(;;)
    {
        //If the task can take the semaphore it means one or more actuator is stalling.
        //A variable (stalling_finger) will contain which one called the interface.
        /*xSemaphoreTake(xSemapStalling, 3);*/
        

        //block until message from top level controller
        xQueueReceive( xTopLevelQueue, &instructions, 0 );
        //instructions is a yet to be defined type since it hasn't been defined. 
        //But for starters let's just assume it's just close and open (0 or 1).

        /* Here we will compare the current state of each finger to the one
        * the instructions received above. It will send instructions to fingers that 
        * are required to move using an intergrated model to plan out the necessary output.
        * It will then be translated into a the physical action (GPIO, PWM, SPI, etc...)
        * required to performed said instruction.
        */


        /* B) Register position/state deducing subroutine (ADC1 read).
         * This function will do the following
         *   1. adc voltage read
         *   2. deduce state from voltage difference from last read.
         *   3. send out result to modeling subroutine.
         */

        //TODO: usage of functions
        finger[efinger]. actuator_state(finger_char_t * fg)


        /* C) Modeling subroutine
         *   1. Choose a speed, //Max speed for now
         *      a) define available speed modes
         *   2. Choose a position and calculate the time required 
         *   3. Send those to the control subroutine
         */

        /* D) Control subroutine
         *   1. Translate speed to PWM pulse width in selected direction 
         *      1.1 State like closing and opening are important because they add a delay to the target speed.
         *          Switching from the opening to closing state has a small delay that has to be considered.
         *   2. set GPIO pin to work for that duration
         *   3. Should we read feed back
         */

         //TODO: Stalling callback
        /* E) Staling detection task to ISR
         * To save processing time, adc reads will not happen when the finger is either closed or opened.
         * This task will remember the last two value and compare it to the most recent one
         * When detected, call upon an CPU interrupt (hold give) to make the finger interface react accordingly.
         * https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/system/intr_alloc.html
         */

        /* F) Shutting down actuator subrotine
         * function call when either stalling is detected or not required. 
         *  1. Stop actuator, both GPIO pulled down
         *  2. Change interface finger state.
         */

        /* G) Deconstructer
         * Terminate all task in interface and power down actuator driver.
         */


    }

    //This should never happen involuntarily.
    vTaskDelete(NULL);
}

//Sensor
static uint32_t Actuator_Pos_volt(adc1_channel_t channel)
{
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
    /*printf("Raw: %d\tVoltage: %dmV\n", adc_reading, voltage);*/

    return voltage;
}


static fg_state_e actuator_state(finger_char_t * fg)
{
    const double mVtomm_slope = -0.006255481443114;
    uint64_t timestamp[3];
    double delta_t;

    double positions[3], cur_position, delta_x;
    double total_speed, speeds[2];
    uint32_t mVolt;
    

    int num_sample;
    //Get samples and timestamps, convert them from mV to mm
    for(num_sample=0; num_sample<3; ++num_sample) {
        timestamp[num_sample] = esp_timer_get_time();
        mVolt = Actuator_Pos_volt(fg.adc_channel);
        //x = mv * slope + b
        cur_position = mvtomm_slope * (double)mVolt;
        cur_position +=19;
        positions[num_sample] = cur_position;

    }
    fg.fg_cur_pos = positions[3];
    ESP_LOGI(ACT_TASK, "MAJEUR");
    ESP_LOGI(ACT_TASK, "positions, 0:%f, 1:%f, 2:%f", positions[0], positions[1], positions[2]);

    //Calculate speeds
    for(calc=0; calc<2; ++calc) {
        delta_t = (double)(timestamp[calc+1] - timestamp[calc]);
        delta_t *= 1000; //Convert us to ms
        delta_x = positions[calc+1] - positions[calc];
        speeds[calc] = delta_x/delta_t;
        total_speed += speeds[calc];
    }
    total_speed /= calc; //speed in mm/ms
    ESP_LOGI(ACT_TASK, "Speed = %f", total_speed);

    ////State guesing logic
    
    //we're definatly moving
    if(total_speed > 4000 || total_speed < -4000) {
        if(total_speed >0) return FG_OPENING;
        if(total_speed <0) return FG_CLOSING;
    }
    //We've almost completly stopped moving
    else if(total_speed < 1000 || total_speed > -1000){
        if(positions >= (fg.max_position - 200) return FG_OPENED;
        if(positions <= (fg.min_position + 200) return FG_CLOSED;
        if(positions > fg.last_set_pos - 100 && 
                    positions < fg.last_set_pos + 100) return FG_SET_POS;
        //were not moving and were not at any valid position, we're stuck
        else return FG_STUCK;
        //add overshoot detection logic and correction here
    }
    //Not going at any valid speed, something must be slowing the finger down.
    else 
        return FG_WEIRD;

}

#define INSTRUCT_FG_OPEN  1.0
#define INSTRUCT_FG_CLOSE 0.0

#define DIR_EXTEND  1
#define DIR_CONTRACT 2
#define DIR_NONE     0

//modeling module
static int finger_mv_planing(finger_char_t fg, double toplvl_instruct)
{
    double delta_x, time_to_target;

   fg.act->set_speed = fg.act->max_speed;
   fg.act->set_time = 0;
   fg.act->direction = DIR_NONE;
   //Instruction is to set to max positon but the finger is already there.
   if(INSTRUCT_FG_OPEN == (int)toplvl_instruct && fg.fg_state == FG_OPENED)
       return 0;

   //Instruction is to set to min positon but the finger is already there.
   if(INSTRUCT_FG_CLOSE == (int)toplvl_instruct && fg.fg_state == FG_CLOSED)
       return 0;

   //Instruction is to set to a set positon but the finger is already there.
   //convert instruction to an actual position
   double target_position = fg.min_position +((fg.max_position - fg.min_position)*instruct);
   //very close to target position 
   if(fg.fg_cur_pos >= target_position-100 && fg.fg_cur_pos <= target_position+100
           && fg.fg_state == FG_SET_POS) {
       return 0;
   }

   delta_x = target_position - fg.fg_cur_pos;
   //Insert speed modulation here. 
   //Top level instruction will have a force and timing add to it, that will help calculate the speed.
   fg.act->set_speed = fg.act->max_speed;
   
   //Finger will close
   if(delta_x < 0) {
       fg.act.direction = DIR_CONTRACT;
       delta_x *= -1; //time should be positive
       time_to_target = (uint64_t)((delta_x / fg.act->set_speed)*1000000); //time to reach in us
   
       //Last we checked, that finger was moving in wrong direction, we need to compensate
       //this needs to be smarter.
       if(fg.fg_state == FG_OPENING)
           fg.act->set_time = time_to_target * 1.2;
   }
   //finger will open
   else {
       fg.act.direction = DIR_EXTEND;
       time_to_target = (uint64_t)((delta_x / fg.act->set_speed)*1000000); //time to reach in us

       //Last we checked, that finger was moving in wrong direction, we need to compensate
       //this needs to be smarter.
       if(fg.fg_state == FG_CLOSING)
           fg.act->set_time = time_to_target * 1.2;
   }
   return 1;
    
}


//control module
static void finger_control_iface(finger_char_t fg)
{
    /* index    io  32 and 33
     * Majeur   io  25 and 26
     * Anulaire io  14 and 27 
     * Auriculaire io 12 and 13
     * When the lower (32,25,14,12) pin is high and the other one is low the actuator contracts
     * and vice-versa. 
     */

    //TODO: Create oneshot time callback
}



