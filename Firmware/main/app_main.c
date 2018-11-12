/*#include "../bluetooth/ble_app.h"*/
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/timers.h"

#include "esp_log.h"

#define mainDELAY_LOOP_COUNT 1000

TaskHandle_t xTask2Handle = NULL;
QueueHandle_t xQueue;


/* Define an enumerated type used to identify the source of the data. */
typedef enum
{
    eSender1,
    eSender2
} DataSource_t;

/* Define the structure type that will be passed on the queue. */
typedef struct
{
    uint8_t ucValue;
    DataSource_t eDataSource;
} Data_t;

/* Declare two variables of type Data_t that will be passed on the queue. */
static const Data_t xStructsToSend[ 2 ] =
{
    { 100, eSender1 }, /* Used by Sender1. */
    { 200, eSender2 } /* Used by Sender2. */
};

void vSenderTask( void *pvParameters )
{
BaseType_t xStatus;


    /*IValueToSend = ( int32_t ) pvParameters;*/
    /*uxPriority = uxTaskPriorityGet( NULL );*/


    for( ;; )
    {
        xStatus = xQueueSendToBack( xQueue, pvParameters, 10 );
        if( xStatus != pdPASS )
            printf( "Could not send to queue.\n" );
        /* Print out the name of this task. */
        /*vTaskDelay(pdMS_TO_TICKS(100));*/
        /*vTaskPrioritySet( xTask2Handle, uxPriority + 1 )*/
    }
}

void vReceiverTask( void *pvParameters )
{
Data_t xReceivedStruct;
BaseType_t xStatus;
const TickType_t xTicksToWait = pdMS_TO_TICKS(100);

    /* As per most tasks, this task is implemented in an infinite loop. */
    for( ;; )
    {
        if (uxQueueMessagesWaiting( xQueue ) != 3 )
            printf(" Queue should have been empty!\n");


        xStatus = xQueueReceive( xQueue, &xReceivedStruct, 0 );
        if( xStatus == pdPASS )
        {
            if(xReceivedStruct.eDataSource == eSender1 )
                printf( "From Sender 1 = %d\n", xReceivedStruct.ucValue );

            if(xReceivedStruct.eDataSource == eSender2 )
                printf( "From Sender 2 = %d\n", xReceivedStruct.ucValue );
        }
        else
            printf("Error in receiving\n");
        /* Print out the name of this task. */

        /* Delay for a period. */
        /*vTaskDelay(pdMS_TO_TICKS(100));*/
    }
}


void app_main()
{

    xQueue = xQueueCreate( 3, sizeof( Data_t ) );

    if( xQueue != NULL )
    {
        xTaskCreate( vSenderTask, "Sender1", 2048, &( xStructsToSend[0] ), 2, NULL );
        xTaskCreate( vSenderTask, "Sender2", 2048, &( xStructsToSend[1] ), 2, NULL );

        xTaskCreate( vReceiverTask, "Receiver", 2048, NULL, 1, NULL );
    }
    else
        printf("Error while creating queue.\n");

    /*bt_app_launch();*/
    for(;;)
    { 
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
