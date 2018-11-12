
#include "freertos/task.h"

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
} finger_e;

//actuator characteristics
typedef struct
{

    uint8_t max_len;
    //Will differ from data sheet since finger weight will be
    uint8_t max_speed; 
} actuator_t;

//Finger characteristics
typedef struct
{
    const finger_e finger;
    const actuator_t act;
    const adc1_channel_t adc_channel;

    //fingertip plana
    coord_t finger_tip_pos;
    //last state time stamp
    int64_t time_stamp; 
    
    
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

