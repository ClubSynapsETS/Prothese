
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
#include "esp_timer.h"
#include "esp_log.h"

#define LOW 0
#define HIGH 1
#define NO_OF_SAMPLES 32
#define DEFAULT_VREF 1100

static const char* TEST_TAG = "ACTUATOR_TEST";


void vActuatorData( void * pvParam );
void config_actuator_channel(void);
static void oneshot_timer_callback(void* arg);


static esp_adc_cal_characteristics_t *adc_chars;
static const adc_channel_t channel = ADC_CHANNEL_6;     //GPIO34 if ADC1, GPIO14 if ADC2
static const adc_atten_t atten = ADC_ATTEN_DB_11;
static const adc_unit_t unit = ADC_UNIT_1;



static void print_char_val_type(esp_adc_cal_value_t val_type);
static void print_char_val_type(esp_adc_cal_value_t val_type)
{
    if (val_type == ESP_ADC_CAL_VAL_EFUSE_TP) {
        printf("Characterized using Two Point Value\n");
    } else if (val_type == ESP_ADC_CAL_VAL_EFUSE_VREF) {
        printf("Characterized using eFuse Vref\n");
    } else {
        printf("Characterized using Default Vref\n");
    }
}

void udelay(uint64_t delay)
{
    uint64_t timestamp = esp_timer_get_time();
    uint64_t curtime = timestamp;

    while(curtime <= timestamp + delay )curtime = esp_timer_get_time();

}

uint32_t adc_return_voltage(void)
{
    uint32_t adc_reading = 0;

    for (int i = 0; i < NO_OF_SAMPLES; i++) 
        adc_reading += adc1_get_raw((adc1_channel_t)channel);
    adc_reading /= NO_OF_SAMPLES;
    return esp_adc_cal_raw_to_voltage(adc_reading, adc_chars);
}

void config_actuator_channel(void)
{
    //Configure ADC
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(channel, atten);

    //Characterize ADC
    adc_chars = calloc(1, sizeof(esp_adc_cal_characteristics_t));
    esp_adc_cal_value_t val_type = esp_adc_cal_characterize(unit, atten, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);
    print_char_val_type(val_type);

    gpio_config_t io_conf;
    io_conf.intr_type = GPIO_PIN_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    //set gpio 26 and 25 
    io_conf.pin_bit_mask = ((1ULL<<26) | (1ULL<<25));
    io_conf.pull_down_en = 0;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);


    //set pin level to low
    gpio_set_level(26, LOW);
    gpio_set_level(25, LOW);

}

void vActuatorData( void * pvParam )
{

    //Config each pin for actuator control
    config_actuator_channel();

    //create esp timer
    const esp_timer_create_args_t oneshot_timer_args = {
            .callback = &oneshot_timer_callback,
            .name = "actuator_ctrl"
    };

    esp_timer_handle_t oneshot_timer;

    ESP_ERROR_CHECK(esp_timer_create(&oneshot_timer_args, &oneshot_timer));

    for(;;)
    { 

        uint32_t voltage = 0;
        //test adc timing char
        uint64_t comparedTime;
        uint64_t timestamp = esp_timer_get_time();

        printf("\n\n");

        voltage = adc_return_voltage();

        comparedTime = esp_timer_get_time() - timestamp;
        ESP_LOGI(TEST_TAG,"ADC %d samples takes %d us to convert", NO_OF_SAMPLES, (uint32_t)comparedTime);
        ESP_LOGI(TEST_TAG,"Voltage = %d mv", voltage);

        //go to min
        double act_max_speed = 28;
        double calculate_pulse_width = 20/act_max_speed; //stroke time interval, in seconds
        calculate_pulse_width *= 1000000; //converte to us
        uint32_t pulse_width = (uint32_t)calculate_pulse_width;

        //Go to initial position
        ESP_LOGI(TEST_TAG, "Extending, pulse width = %d", pulse_width);
        gpio_set_level(26, HIGH);
        udelay(pulse_width); //taking into consideration the acceleration
        gpio_set_level(26, LOW);

        udelay(2000000);

        voltage = adc_return_voltage();
        ESP_LOGI(TEST_TAG, "Supposed min position has =%d", voltage);

        int iter;
        for(iter=0; iter<20; iter+=1)
        {
            calculate_pulse_width = 1 / act_max_speed;
            calculate_pulse_width *= 1000000; //converte to us
            pulse_width = (uint32_t)calculate_pulse_width;

            printf("PULSE WIDTH = %d\n", pulse_width);
            gpio_set_level(25, HIGH);
            udelay(pulse_width); //taking into consideration the acceleration
            gpio_set_level(25, LOW);

            timestamp = esp_timer_get_time();
            voltage = adc_return_voltage();
            comparedTime = esp_timer_get_time() - timestamp;
            ESP_LOGI(TEST_TAG,"ADC %d samples takes %d us to convert", NO_OF_SAMPLES, (uint32_t)comparedTime);
            ESP_LOGI(TEST_TAG,"Voltage = %d mv", voltage);


            vTaskDelay(pdMS_TO_TICKS(1500));
        }

    }

}
