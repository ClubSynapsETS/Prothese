#ifndef APP_MAIN_H
#define APP_MAIN_H

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/timers.h"

#include <stdio.h>
#include <stdlib.h>
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
#include "esp_log.h"

#include "../bluetooth/ble_app.h"
#include "../Motion_control/finger_interface.h"

#define TASK_FINGER_IFACE_PRIORITY  1

// container for incoming ble data
typedef struct{
    uint64_t myo_pose; 
    uint64_t data_read;
    const char* finger_iface_task_name;
    TaskHandle_t finger_iface_handle;
    uint64_t tast_created;
} bt_shared_data_t;

#endif