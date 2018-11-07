/*---------------------------------*/
#ifndef __GLOBAL_MESSAGE_LIST__
#define __GLOBAL_MESSAGE_LIST__

#include "freertos/FreeRTOS.h"
#include "freertos/message_buffer.h"

/*Description
 * - Each module created stacks it's flag and variables it want's to share onto the global_message_stack.
 * - After all modules have been initialized,
 *       tasks will be able copy a link to specific information and read but not edit their content.
 * - The message_buffer module block a task until the receive method is complete, so expect slight delays.
*/
/* Typical Dynamique list node parameters definition */

typedef struct mess_node  * t_link_list;

typedef struct mess_node 
{
    char * message_name;
    MessageBufferHandle_t n;
    t_link_list next_node;
} t_mess_node;

/* List node constructor */
t_link_list init_node_list(char * mess_name, const MessageBufferHandle_t * src, t_link_list next_node);

/* Typical list structure definition */
typedef struct mess_list {
    /* List size parameter*/
    int size;
    /* List pointer position parameter*/
    int cur_pos;

    /* List pointer to first node parameter*/
    t_link_list first_node;
    /* List pointer to last node parameter*/
    t_link_list last_node;
    /* List pointer to current node parameter*/
    t_link_list cur_node;
} t_mess_list;

/* xMessage list constructor */
t_mess_list init_mess_list(void);


/* -------------------------------------------------- */
/* Public list interaction */

//Get list size
int get_size_mess_list(const t_mess_list* lst);

// Get position of the tracker inside of the message list
int get_position_mess_list(const t_mess_list* lst);

//Use name to return messagebuffer handle, 1 fond
int find_message_by_name(const t_mess_list* lst, char * mess_name, MessageBufferHandle_t * dest);
// return the message buffer handle under the tracker
#endif
