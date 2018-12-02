
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_timer.h"

#include <stdint.h>

//Fingers on hand, excluding thumb.
typedef enum
{
    index0, //Index
    majeur1, //Majeur
    anulaire2, //Anulaire
    auriculaire3  //Auriculaire
} finger_id_e;

//finger possible state
typedef enum
{
    FG_CLOSED, // Voltage to position ~ min position
    FG_CLOSING, // Voltage going toward max ( check sign of calculated slope(+))
    FG_INVALID,// Position not min nor max and slope ~ 0 // difficult to determin?
    FG_SET_POS, // SAme as Stuck but the controller set this positoon
    FG_OPENING, // Voltage going toward min ( slope sign (-))
    FG_OPENED, // Voltage to position ~ max positio
    FG_WEIRD
} fg_state_e;

//actuator characteristics
typedef struct
{
    uint64_t set_time;
    double set_speed;
    int direction;

    //Will differ from data sheet since finger weight will be;
    double max_speed; 
} actuator_instruct_t;

//Finger characteristics
typedef struct
{
    finger_id_e finger_id;
    fg_state_e state;
    double cur_position;
    double last_set_pos;
    uint32_t stroke_num;

    actuator_instruct_t * act;
    //finger specfic hardware interface
    adc1_channel_t adc_channel;
    gpio_num_t upper_gpio;
    gpio_num_t lower_gpio;

    //finger specific characteristic
    double max_position;
    double min_position;

    //last state time stamp
    uint64_t time_stamp; 
    //timer handler, it will lower gpio level when called
    esp_timer_handle_t timer_handle;
} finger_charc_t;


/**************************************************************************/
/* Task prototype for main control management.                            */
/**************************************************************************/
void vFingerInterface( void * pvParam );


/**************************************************************************/
/* static functions prototypes for finger iface                           */
/**************************************************************************/
    
/*configure pins*/
//static void config_actuator_channel(finger_charc_t * fg);

/**
 * @brief Get voltage outputed by the actuator refering to it's position.
 *
 * @param channel: adc channel to read.
 *
 * @return volatge: voltage in mV read on channel
 */
//static uint32_t Actuator_Pos_volt(adc1_channel_t channel);

/**
 * @brief Mesure position by reading the actuator's potentiometer voltage and assigning a time stamp.
 *        doing this multiple time we can detecte mouvement and direction. With these, the state can 
 *        be determined.
 *
 * @param fg: Finger that will me teste for state.
 *
 * @return state: See fg_state_e for full list of possible state.
 */
//static fg_state_e actuator_state(finger_charc_t * fg);

/**
 * @brief Plan out mouvement of finger using position, state and toplevel instruction. It will edit
 *        the pq12_charact structure set_time, set_speed, and direction for lower level control.
 *        NOTE: When the instruction is the same as the current state, nothing will be done.
 *
 * @param fg: Finger to plan mouvement.
 * @param toplvl_instruct: Currently the value is between 0 and 1, 0 being min positon and 1 being max.
 *
 * @return Action/Inaction: 0 if no action will be taken, 1 if a pulsse must be sent to conform to instruction.
 */
//static int finger_mouvement_planing(finger_charc_t * fg, double toplvl_instruct);

/**
 * @brief Simple callback after a delay in microseconds, used to set GPIO level of actuator to low.
 *
 * @param arg: This is a void pointer to a finger_charc_t type, which contains said gpio channel.
 *
 * @return None.
 */
//static void actuator_timer_callback(void* arg);

/**
 * @brief Hardware level control of an actuator, currently it only requires a pulse on a pin to contract
 *        or extend the shaft. I will set a gpio channel to high, then starts a timer for when it is due to
 *        set to low (pulse width).
 *
 * @param fg: Finger to control.
 *
 * @return None
 */
//static void finger_control_iface(finger_charc_t * fg);
