
#include "freertos/task.h"
#include "driver/gpio.h"

#include <stdint.h>
#include <math.h>

typedef struct
{
    uint8_t x,y;
} coord_t;

//Fingers on hand, excluding thumb.
typedef enum
{
    efinger0, //Index
    efinger1, //Majeur
    efinger2, //Anulaire
    efinger3  //Auriculaire
} finger_id_e;

//finger possible state
typedef enum
{
    FG_CLOSED, // Voltage to position ~ min position
    FG_CLOSING, // Voltage going toward max ( check sign of calculated slope(+))
    FG_STUCK,// Position not min nor max and slope ~ 0 // difficult to determin?
    FG_SET_POS; // SAme as Stuck but the controller set this positoon
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

    gpio_num_t upper_gpio;
    gpio_num_t lower_gpio;

    //Will differ from data sheet since finger weight will be;
    double max_speed; 
} actuator_instruct_t;

//Finger characteristics
typedef struct
{
    finger_id_e finger_id;
    fg_state_e fg_state;
    double fg_cur_pos;

    actuator_instruct_t * act;
    adc1_channel_t adc_channel;

    //finger specific characteristic
    double max_positon;
    double min_positon;
    double last_set_pos;

    //last state time stamp
    int64_t time_stamp; 
    //timer callback function pointer?
} finger_charc_t;

/**
 * @brief Get voltage outputed by the actuator refering to it's position.
 *
 * @param unit: Unit of the adc, either ADC_UNIT_1 or ADC_UNIT_2
 * @param channel: adc channel to read.
 *
 * @return volatge: voltage in mV read on channel
 */
uint32_t vActuator_Position(adc_unit_t unit, uint8_t channel)

