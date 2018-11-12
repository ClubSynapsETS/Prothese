
#include <math.h>

#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include <math.h>

#include "adc/adc_position.h"


static const actuator_t pq12_charact
{
    max_len = 20; //in mm
    max_speed = 28; //in mm/s
}

static finger_charc_t xfingerCharac[4] =
{
    { efinger0, pq12_charact, ADC1_CHANNEL_0, {0,0}, 0 },
    { efinger1, pq12_charact, ADC1_CHANNEL_3, {0,0}, 0 },
    { efinger2, pq12_charact, ADC1_CHANNEL_6, {0,0}, 0 },
    { efinger3, pq12_charact, ADC1_CHANNEL_7, {0,0}, 0 }
};


//Modeling
/*void */

//Sensor
uint32_t Actuator_Position(adc1_channel_t channel)
{
const uint8_t no_samples = 64;
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


static finger_e stalling_finger;


/*Module main finger interface*/
void vFingerInterface( void * pvParam )
{
BaseType_t xStatus;
QueueHandle_t xFingerQueue, xTopLevelQueue;
SemaphoreHandle_t xSemapStalling


    for(;;)
    {
        //If the task can take the semaphore it means one or more actuator is stalling.
        //A variable (stalling_finger) will contain which one called the interface.
        xSemaphoreTake(xSemapStalling, 3);
        

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

        /* A) Define finger states 
         *   1. closed
         *   2. closing
         *   3. stalling_closing
         *   4. stopped
         *   5. stalling_openning
         *   6. opening
         *   7. opened
         *   8. stuck //Not considered
         */

        /* B) Register position/state deducing subroutine (ADC1 read).
         * This function will do the following
         *   1. adc voltage read
         *   2. deduce state from voltage difference from last read.
         *   3. send out result to modeling subroutine.
         */

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
