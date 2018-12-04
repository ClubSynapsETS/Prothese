#include "app_main.h"

/*
QueueHandle_t fgIfaceQueue;
static const char * MAIN_TASK = "MAIN_CTRLER";
*/

//Test finger interface function
/*
void test_fg_iface(void)
{
    double instruct[4] = { 0.5, 0.5, 0.5, 0.5 };

    xQueueSend(fgIfaceQueue, (void*)instruct, (TickType_t)0);
    
    vTaskDelay(pdMS_TO_TICKS(50000));
    instruct[0] = 0.0;
    instruct[0] = 1.0;
    instruct[0] = 0.7;
    instruct[3] = 0.3;


    xQueueSend(fgIfaceQueue, (void*)instruct, (TickType_t)0);

}
*/

// Old entry point
/*void app_main()
{
    BaseType_t xStatus;
    
    bt_app_launch();

    fgIfaceQueue = xQueueCreate(4, sizeof(double) );
    if(fgIfaceQueue == NULL)
        ESP_LOGE(MAIN_TASK, "Unable to create fg iface queue, suspending...");

    xTaskCreate( vFingerInterface, "Finger IFace", 8056, &fgIfaceQueue, TASK_FINGER_IFACE_PRIORITY, NULL);

    ESP_LOGI(MAIN_TASK, "Entering the app_main main loop.");
    
    for(;;)
    { 
        test_fg_iface();

        vTaskDelay(pdMS_TO_TICKS(1000));

    }
}
*/


// creating a global shared structure for incoming instructions
volatile bt_shared_data_t bt_shared_buffer = {.myo_pose = 0, .data_read=1, 
                                              .finger_iface_task_name = "Finger_Interface",
                                              .finger_iface_handle = NULL,
                                              .tast_created=0}; 


void app_main(){

    // lauching the BT client
    bt_app_launch();

    for(;;){ 
        vTaskDelay(pdMS_TO_TICKS(2000));
    }

}

