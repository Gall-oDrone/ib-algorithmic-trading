#!/bin/bash

conda init zsh
# Temporarily disable auto-activation of the base environment
conda config --set auto_activate_base false

env_name="ib_algotrading"

# Check if any Anaconda environment is active
current_env=$(conda info --envs | grep '*' | awk '{print $1}')

# If an environment is active (not "base"), deactivate it
if [ "$current_env" != "" ] && [ "$current_env" != "base" ]; then
    echo "Deactivating current environment: $current_env"
    conda deactivate || { echo "Error: Failed to deactivate environment: $current_env"; exit 1; }
else
    echo "No active environment to deactivate."
fi

# Source the Anaconda activation script
. /opt/anaconda3/bin/activate || { echo "Error: Failed to source the Anaconda activation script."; exit 1; }

# Activate the desired Anaconda environment
conda activate /opt/anaconda3/envs/$env_name || { echo "Error: Failed to activate the $env_name environment."; exit 1; }

# Verify the activation
which python || { echo "Error: Python not found in the $env_name environment."; exit 1; }

# Optionally show the current environment name (debugging)
echo "Current environment: $(conda info --envs | grep '*' | awk '{print $1}')"
