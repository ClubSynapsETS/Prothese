
#include <math.h>
#include <stdlib.h>

#define MYO_CHANNEL_SIZE 8
#define MYO_BUFFER_SIZE 50*8
#define MYO_SAMPLE_SIZE 25
#define MID_SAMPLE_INDEX 12

#define MODEL_NUM_LABEL 5
#define MODEL_NO_LABEL -1

static const char* CLASSI_TASK = "CLASSIFIER TASK"



//50 data point and 8 channel
static int myo_raw_data[MYO_BUFFER_SIZE][MYO_CHANNEL_SIZE];


void vPipeline_Pose( void * pvParam )
{
    int idx, channel, n_samples;
    int sample[MYO_SAMPLE_SIZE];
    double rms_vector[2][MYO_SAMPLE_SIZE];
    double scaled_rms_vector[2][MYO_SAMPLE_SIZE];

    int classifier_result[2];

    for(;;)
    {

        //Receive data from Myo

        //separate dataframe into two samples
        for(n_samples=0; n_samples<2; n_samples++)
        {
            //Identify sample
            for(channel=0; channel<MYO_CHANNEL_SIZE; channel++)
            {
                for(idx=0; i<MYO_SAMPLE_SIZE; idx++)
                    sample[idx] = myo_raw_data[idx][chan];

                //Get rms for this sample
                rms_vector[n_samples][channel] = calculate_rms(sample)
            }

            //Scale data
            scaled_rms_vector[n_samples] = standardScaler(rms_vector[n_samples]);

            //Classify using model data
            classifier_result[n_samples] = classifier(scaled_rms_vector[n_samples]);

        }


        //Wait for more data to come in
        vTaskDelay(pdMS_TO_TICKS(250));

    //End of endless loop
    }

    vTaskDelete(NULL);
}

/*
 * Calculate the Root Mean Square RMS of a given data sample on a single channel.
 */
static double* calculate_rms(int* sample)
{
    int idx;

    //Square values
    for(idx=0; idx<MYO_SAMPLE_SIZE; idx++)
        sample *= sample;

    //find the mean
    qsort(sample, MYO_SAMPLE_SIZE, sizeof(int), low_to_high);
    mean = sample[MID_SAMPLE_INDEX]
    //Square it
    return sqrt(mean)
}


//comparison function
static int low_to_high (const void * p1, const void * p2) 
{
    int f = *((int*)elem1);
    int s = *((int*)elem2);
    if (f > s) return  1;
    if (f < s) return -1;
    return 0;
}

//  scaled_Data = (x-mean)/var 
static double* standardScaler(double* rms_vec)
{

    double scaled_data[MYO_CHANNEL_SIZE];
    int idx;

    for(idx=0; idx<MYO_CHANNEL_SIZE; idx++)
        scaled_data[idx] = (rms_vec[idx] - scaler_mean[idx]) / scaler_var[idx];

    return scaled_data;

}

int classifier(double* scaled_rms_vector)
{
    int idx, label;
    double sum_total=0;

    for(label=0; label<MODEL_NUM_LABEL; label++)
    {
        //Dot product of the two vectors + a const
        for(idx=0; idx<MYO_CHANNEL_SIZE; idx++)
            sum_total += scaled_rms_vector[idx]*label_coef[label][idx];

        if(sum_total + label_instance[label] > 0)
            return label;

    }
    return -1;

}

//Constants found by a external model
const double scaler_mean[MYO_CHANNEL_SIZE] = 
                { 15.27278823, 20.61739096, 26.63235968, 29.25970425,
                  22.88020618, 10.74633017, 15.01194675, 12.44157631 };
const double scaler_var[MYO_CHANNEL_SIZE] = 
                { 15.85038121, 18.33252677, 20.01025644, 22.94854805, 
                  18.76962492, 9.90608964, 20.21452028, 15.04835818 };
 
const double label_instance[MODEL_NUM_LABEL] =
                    {-2.398348805, -3.14545329, -0.9394784, -5.1253857, -1.06435720 };

const double label_coef[MODEL_NUM_LABEL][MYO_CHANNEL_SIZE] = {
        //Rest
        { -0.50177779, -0.12312444, -0.58211669, -1.13062525, 
          -0.0527867, -0.5822092 , -0.26278155, -0.30333588 },

        //Hand_open
        {  0.71718695,  0.79855272,  1.59690406, -1.12807493, 
           0.01190395, -0.14929037, -5.3280771, -0.09335204 },

        //Hand_close
        { 0.50595334,  0.12428787, -0.50990965, 1.04564593, 
         -0.21602766, -0.63562547, -0.04528732, -0.12135293 },

        //Wrist_extension
        { -7.96583171, -0.34874807, 0.44085694, 0.53103972, 
          0.10330688, 1.71613716, -1.35682156, 1.80796014 },

        //Wrist_flexion
        { -0.80088942, 0.77656629, -0.00487294, 0.266677,
          -0.76825635, -0.3232368, 3.40921772, 0.26942154 }
        
    };
