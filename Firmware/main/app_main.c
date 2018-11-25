/*#include "../bluetooth/ble_app.h"*/
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/timers.h"

#include "../bluetooth/ble_app.h"
#include "../Motion_control/finger_interface.h"

#include <stdio.h>
#include <stdlib.h>
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
#include "esp_log.h"


#define TASK_FINGER_IFACE_PRIORITY  4

QueueHandle_t fgIfaceQueue;

static const char * MAIN_TASK = "MAIN_CTRLER";

//Test finger interface function
void test_fg_iface(void)
{
    double instruct[4] = { 0.5, 0.5, 0.5, 0.5 };

    xQueueSend(fgIfaceQueue, (void*)instruct, (TickType_t)0);
    
    vTaskDelay(pdMS_TO_TICKS(50));
    instruct[0] = 0.0;
    instruct[0] = 1.0;
    instruct[0] = 0.7;
    instruct[3] = 0.3;



}


void app_main()
{
    BaseType_t xStatus;
    /*bt_app_launch();*/

    fgIfaceQueue = xQueueCreate(4, sizeof(double) );
    if(fgIfaceQueue == NULL)
        ESP_LOGE(MAIN_TASK, "Unable to create fg iface queue, suspending...");

    xTaskCreate( vFingerInterface, "Finger IFace", 8056, &fgIfaceQueue, TASK_FINGER_IFACE_PRIORITY, NULL);
    
    for(;;)
    { 

        vTaskDelay(pdMS_TO_TICKS(1000));

    }
}
